"""
ATOM-Pi Wake Word Listener (EARS, stage 1)
===========================================
Always-on wake word -> hands the microphone to the backend's Whisper
capture -> waits until ATOM has finished speaking -> re-arms.

VERIFIED AGAINST REAL CODE (pocket-ai chat_ai.py):
  * WebSocket endpoint:  ws://localhost:8000/ws/voice
  * Message format:      {"type": "toggle_voice"}   (NOT "command")
  * toggle_voice #1  -> backend starts Whisper mic capture
  * toggle_voice #2  -> backend stops capture, transcribes, reasons,
                        speaks; emits {"type":"voice_status",
                        "status": listening|thinking|speaking|idle}
  * Those voice_status events are the same ones the GUI robot uses.

WAKE PHRASE: "Hey ATOM" — and only that.
  Wake phrases are trained model files, not strings: this listener
  loads hey_atom.onnx from the app folder (path configurable via
  WAKEWORD_MODEL in .env). If the file is missing it explains how to
  train it (openWakeWord's Colab notebook; duration depends on
  dataset and validation results) and exits —
  it never falls back to some other phrase. Until the model exists,
  the touchscreen mic button drives voice as normal.

MIC CONTENTION (the classic single-microphone problem):
  This listener CLOSES its microphone stream before telling the
  backend to capture, and only reopens it after the backend reports
  status "idle" — so the two never fight over the device, and ATOM's
  own speech can never re-trigger the wake word.

Run (backend must be up):
    cd ~/pocket-ai && source .venv/bin/activate && python wakeword_listener.py

Requires: pip install openwakeword onnxruntime websocket-client requests
"""

import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pyaudio
import websocket

# Imported defensively rather than at module scope. openwakeword/__init__.py
# imports scikit-learn transitively, so a venv missing it raises
# ModuleNotFoundError right here — before main() can explain what to do, and
# in a way start-atom.sh's `until python ...` turns into a restart loop.
# feature_models_missing() reports _OWW_IMPORT_ERROR as actionable text.
try:
    from openwakeword.model import Model
    _OWW_IMPORT_ERROR = None
except Exception as _exc:            # pragma: no cover - environment guard
    Model = None
    _OWW_IMPORT_ERROR = _exc

try:
    # Proper polyphase resampling (anti-aliased). scipy is already a pinned
    # pocket-ai dependency, so this is available on every real install; the
    # np.interp fallback below only runs in a stripped environment.
    from scipy.signal import resample_poly
except Exception:
    resample_poly = None

# ----------------------------- settings (env-overridable) ----------
BACKEND = os.environ.get("ATOM_BACKEND", "http://localhost:8000")
WS_URL = BACKEND.replace("http", "ws") + "/ws/voice"
WAKE_MODEL = os.environ.get("WAKEWORD_MODEL", "hey_atom.onnx")
THRESHOLD = float(os.environ.get("WAKEWORD_THRESHOLD", os.environ.get("WAKE_THRESHOLD", "0.5")))
LISTEN_SECONDS = float(os.environ.get("LISTEN_SECONDS", "6"))
COOLDOWN = float(os.environ.get("WAKEWORD_COOLDOWN", os.environ.get("WAKE_COOLDOWN", "2")))
CAMERA_ON_WAKE = os.environ.get("CAMERA_ON_WAKE", "1") != "0"
BARGE_IN = os.environ.get("BARGE_IN", "1") != "0"
BARGE_THRESHOLD = float(os.environ.get("WAKE_THRESHOLD_BARGE", "0.7"))
ACK_SOUND = Path(__file__).parent / "sounds" / "ack.wav"
INPUT_DEVICE_INDEX = None  # None = default mic

OWW_RATE, CHUNK = 16000, 1280  # openWakeWord: 16 kHz, 80 ms frames


def pick_input_rate(pa, device_index):
    """Hardware-aware rate pick (many USB mics refuse 16 kHz)."""
    info = (pa.get_device_info_by_index(device_index)
            if device_index is not None
            else pa.get_default_input_device_info())
    for rate in (16000, 48000, 44100, 32000, 22050):
        try:
            if pa.is_format_supported(rate, input_device=int(info["index"]),
                                      input_channels=1,
                                      input_format=pyaudio.paInt16):
                return rate
        except ValueError:
            continue
    return int(info["defaultSampleRate"])


def resample_16k(frame, src):
    """Downsample a hardware frame to openWakeWord's 16 kHz.

    Uses polyphase resampling, which low-pass filters before decimating.
    Plain linear interpolation (the previous form, kept as a fallback) has
    no anti-alias filter: at 48 kHz it folded everything above 8 kHz back
    into the speech band, feeding the model audio that does not match the
    clean 16 kHz clips it was trained on and costing real detection
    accuracy. Output length is pinned so every frame stays exactly 1280
    samples, which the barge-in loop relies on.
    """
    if src == OWW_RATE:
        return frame
    want = int(round(len(frame) * OWW_RATE / src))
    if resample_poly is not None:
        from fractions import Fraction
        f = Fraction(OWW_RATE, src).limit_denominator(1000)
        out = resample_poly(frame.astype(np.float32), f.numerator, f.denominator)
    else:
        dur = len(frame) / src
        x_old = np.linspace(0, dur, num=len(frame), endpoint=False)
        x_new = np.linspace(0, dur, num=want, endpoint=False)
        out = np.interp(x_new, x_old, frame)
    if len(out) > want:
        out = out[:want]
    elif len(out) < want:
        out = np.pad(out, (0, want - len(out)))
    return np.clip(out, -32768, 32767).astype(np.int16)


def feature_models_missing() -> str:
    """Return a human explanation if openWakeWord's shared feature models are
    absent, else "".

    openWakeWord ships NO model binaries in its wheel: every Model() builds an
    AudioFeatures, which loads melspectrogram.onnx and embedding_model.onnx
    from the package's own resources/models directory. When they are missing
    onnxruntime raises a bare NO_SUCHFILE deep inside the constructor — and
    because start-atom.sh runs this listener under `until python ...`, a crash
    here becomes a restart every 3 seconds forever. Detect it first and exit
    cleanly (status 0) so the watchdog stops instead of spinning.
    """
    if _OWW_IMPORT_ERROR is not None:
        exc = _OWW_IMPORT_ERROR
        return (f"openWakeWord is not importable ({exc}).\n"
                "  Install its dependencies inside the app venv:\n"
                "    cd ~/pocket-ai && source .venv/bin/activate\n"
                "    pip install --no-deps openwakeword==0.6.0\n"
                "    pip install 'scikit-learn>=1,<2'")
    import openwakeword
    res = Path(openwakeword.__file__).parent / "resources" / "models"
    missing = [n for n in ("melspectrogram.onnx", "embedding_model.onnx")
               if not (res / n).exists()]
    if not missing:
        return ""
    return ("openWakeWord's shared feature models are not downloaded "
            f"({', '.join(missing)}).\n"
            "  These are separate from hey_atom.onnx and are required by it.\n"
            "  With the Pi online, fix it with:\n"
            "    bash ~/atom-pi/install.sh --sync\n"
            "  or directly:\n"
            "    cd ~/pocket-ai && source .venv/bin/activate\n"
            "    python -c \"import openwakeword.utils as u; "
            "u.download_models(model_names=['hey_atom'])\"")


def open_stream_with_retry(open_stream, attempts=5, delay=0.25):
    """Open the mic, tolerating a backend that has not let go of it yet.

    After handing capture to the backend we reopen the device almost
    immediately for barge-in. ALSA may still have it briefly, and PyAudio
    raises rather than waiting — which used to kill the listener outright
    and hand it to the watchdog. Retry briefly, then give up gracefully.
    """
    for i in range(attempts):
        try:
            return open_stream()
        except Exception as exc:
            if i == attempts - 1:
                print(f"  !! microphone still busy ({exc}) — "
                      "continuing without barge-in for this exchange")
                return None
            time.sleep(delay)
    return None


def play_ack():
    if ACK_SOUND.exists():
        dev = os.environ.get("TTS_ALSA_DEVICE", "default")
        subprocess.Popen(["aplay", "-q", "-D", dev, str(ACK_SOUND)])


def start_camera():
    if not CAMERA_ON_WAKE:
        return
    try:
        import requests
        requests.post(f"{BACKEND}/camera/start", timeout=3)
        print("  -> camera on for this voice session")
    except Exception:
        pass  # already on, or not connected — non-fatal


def run_voice_session(open_stream, model):
    """One full voice exchange with optional BARGE-IN:
    start capture -> listen window -> stop (ATOM thinks/speaks) ->
    while ATOM is thinking/speaking, keep the mic open and watch for
    the wake word at a HIGHER threshold; hearing it sends "abort"
    (the backend also clears its TTS queue — verified patch) and a
    fresh exchange begins. Ends when the backend reports idle.

    Echo caveat: barge-in listens while the speaker plays. The custom
    hey_atom model rarely appears in ATOM's own speech, and the raised
    threshold guards the rest — but with the mic right against the
    speaker, set BARGE_IN=0 in .env."""
    try:
        ws = websocket.create_connection(WS_URL, timeout=5)
    except Exception as exc:
        print(f"  !! backend unreachable at {WS_URL}: {exc}")
        return
    try:
        while True:  # loops on each barge-in
            ws.send(json.dumps({"type": "toggle_voice"}))   # start capture
            print(f"  -> listening for {LISTEN_SECONDS:.0f}s ...")
            time.sleep(LISTEN_SECONDS)
            ws.send(json.dumps({"type": "toggle_voice"}))   # stop + respond
            print("  -> handed to ATOM (thinking/speaking)")
            stream = open_stream_with_retry(open_stream) if BARGE_IN else None
            interrupted = False
            ws.settimeout(0.05 if BARGE_IN else 120)
            try:
                while True:                                 # drain until idle
                    try:
                        msg = json.loads(ws.recv())
                    except websocket.WebSocketTimeoutException:
                        msg = None          # no traffic yet — keep draining
                    except Exception as exc:
                        # The socket is broken (closed, reset, garbage frame).
                        # Bail out of the whole session: the old code set
                        # msg={}, which is falsy, so the intended break was
                        # unreachable and this spun at 100% CPU forever.
                        print(f"  !! lost the backend mid-session: {exc}")
                        return
                    if msg:
                        if msg.get("type") == "voice_transcription":
                            print(f"     heard: {msg.get('text', '')!r}")
                        if (msg.get("type") == "voice_status"
                                and msg.get("status") == "idle"):
                            break
                    if stream is not None:
                        # One hardware frame == exactly 80 ms == 1280 samples
                        # after resampling, at every rate pick_input_rate can
                        # return. Reading a fixed CHUNK*3 here produced ragged
                        # frames (e.g. 1393 samples at 44.1 kHz).
                        raw = stream.read(stream.atom_chunk,
                                          exception_on_overflow=False)
                        frame = resample_16k(np.frombuffer(raw, dtype=np.int16),
                                             stream.atom_rate)
                        if max(model.predict(frame).values(),
                               default=0.0) >= BARGE_THRESHOLD:
                            print("  !! barge-in: wake word during speech — interrupting")
                            ws.send(json.dumps({"type": "abort"}))
                            model.reset()
                            interrupted = True
                            break
            finally:
                # Always hand the mic back, even on an exception — otherwise
                # the re-arm in main() opens a second stream on a busy device.
                if stream is not None:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass
            if not interrupted:
                break
            play_ack()
    finally:
        try:
            ws.close()
        except Exception:
            pass


def main():
    # Resolve the model path (relative paths are relative to this file)
    model_path = Path(WAKE_MODEL)
    if not model_path.is_absolute():
        model_path = Path(__file__).parent / model_path
    if not model_path.exists():
        print("=" * 62)
        print("  Wake model not found:", model_path)
        print()
        print("  ATOM's wake phrase is 'Hey ATOM', which needs a one-time")
        print("  trained model file (hey_atom.onnx). Train it free with")
        print("  openWakeWord's Colab notebook (how long depends on your")
        print("  dataset and validation results):")
        print("    github.com/dscripka/openWakeWord -> 'training new models'")
        print("    target phrase: hey atom")
        print("  Then place hey_atom.onnx next to this file (or in the")
        print("  atom-pi repo root before installing).")
        print()
        print("  Until then: the touchscreen mic button works as normal.")
        print("=" * 62)
        raise SystemExit(0)
    problem = feature_models_missing()
    if problem:
        print("=" * 62)
        print("  Wake word cannot start.")
        print()
        print(" ", problem.replace("\n", "\n "))
        print()
        print("  Until then: the touchscreen mic button works as normal.")
        print("=" * 62)
        raise SystemExit(0)   # 0 = do not let the watchdog restart-loop
    try:
        model = Model(wakeword_models=[str(model_path)],
                      inference_framework="onnx")
    except TypeError:
        # older openwakeword API (<=0.4.x) — installer pins 0.6.0, but
        # survive a mismatched environment rather than crash the ears
        print("note: old openwakeword API detected — using legacy loader")
        model = Model(wakeword_model_paths=[str(model_path)])
    phrase = model_path.stem.replace("_", " ")
    print(f"Wake model loaded — say: '{phrase}'")

    pa = pyaudio.PyAudio()
    hw_rate = pick_input_rate(pa, INPUT_DEVICE_INDEX)
    hw_chunk = int(CHUNK * hw_rate / OWW_RATE)

    def open_stream():
        s = pa.open(format=pyaudio.paInt16, channels=1, rate=hw_rate,
                    input=True, frames_per_buffer=hw_chunk,
                    input_device_index=INPUT_DEVICE_INDEX)
        # Tags for the barge-in resampler. Namespaced: PyAudio's Stream uses
        # `_rate` internally, so writing that name shadows library state.
        s.atom_rate = hw_rate
        s.atom_chunk = hw_chunk
        return s

    stream = open_stream()
    print(f"Mic at {hw_rate} Hz "
          f"({'native' if hw_rate == OWW_RATE else 'resampling'}). "
          "Ctrl+C to stop.")
    try:
        while True:
            raw = stream.read(hw_chunk, exception_on_overflow=False)
            frame = resample_16k(np.frombuffer(raw, dtype=np.int16), hw_rate)
            prediction = model.predict(frame)
            score = max(prediction.values(), default=0.0)
            if score >= THRESHOLD:
                print(f"Wake word detected ({score:.2f})")
                # release the mic BEFORE the backend grabs it
                stream.stop_stream()
                stream.close()
                play_ack()
                start_camera()
                run_voice_session(open_stream, model)
                model.reset()
                time.sleep(COOLDOWN)
                stream = open_stream_with_retry(open_stream)   # re-arm
                if stream is None:
                    print("  !! could not reopen the microphone — stopping "
                          "so the watchdog can restart cleanly.")
                    raise SystemExit(1)
                print("Re-armed. Listening for wake word...")
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        pa.terminate()


if __name__ == "__main__":
    main()
