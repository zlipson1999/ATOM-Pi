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
from openwakeword.model import Model

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
    if src == OWW_RATE:
        return frame
    dur = len(frame) / src
    x_old = np.linspace(0, dur, num=len(frame), endpoint=False)
    x_new = np.linspace(0, dur, num=int(dur * OWW_RATE), endpoint=False)
    return np.interp(x_new, x_old, frame).astype(np.int16)


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
            stream = open_stream() if BARGE_IN else None
            interrupted = False
            ws.settimeout(0.05 if BARGE_IN else 120)
            while True:                                     # drain until idle
                try:
                    msg = json.loads(ws.recv())
                except websocket.WebSocketTimeoutException:
                    msg = None
                except Exception:
                    msg = {}
                if msg:
                    if msg.get("type") == "voice_transcription":
                        print(f"     heard: {msg.get('text', '')!r}")
                    if msg.get("type") == "voice_status" and msg.get("status") == "idle":
                        break
                    if msg == {}:
                        break
                if stream is not None:
                    raw = stream.read(int(CHUNK * 3), exception_on_overflow=False)
                    frame = resample_16k(np.frombuffer(raw, dtype=np.int16), stream._rate)
                    if max(model.predict(frame).values(), default=0.0) >= BARGE_THRESHOLD:
                        print("  !! barge-in: wake word during speech — interrupting")
                        ws.send(json.dumps({"type": "abort"}))
                        model.reset()
                        interrupted = True
                        break
            if stream is not None:
                stream.stop_stream(); stream.close()
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
        s._rate = hw_rate  # tag for the barge-in resampler
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
                stream = open_stream()   # re-arm
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
