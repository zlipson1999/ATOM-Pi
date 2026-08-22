#!/usr/bin/env python3
"""
validate_model.py — prove hey_atom.onnx before it touches the Pi,
then prove it again ON the Pi with --live.

Dataset mode (run wherever the model + recordings are):
    pip install openwakeword onnxruntime numpy
    python validate_model.py hey_atom.onnx --data data/

  Replays every WAV through the model in the EXACT frame format the
  ATOM listener uses (16 kHz mono int16, 1280-sample frames), records
  each clip's peak score, sweeps thresholds 0.30-0.90, and reports:
  positives caught, negatives falsely triggered, and the suggested
  WAKEWORD_THRESHOLD. Refuses to bless a model that misses positives
  or fires on your similar-phrase negatives.

Live mode (on the Pi, in the robot's real room):
    python validate_model.py hey_atom.onnx --live

  Streams the actual microphone and prints scores in real time —
  speak, play the TV, let ATOM talk; watch what the model does.
  This is the tool VALIDATION.md Phase 2 is scored with.
"""

import argparse
import sys
import wave
from pathlib import Path

import numpy as np

try:
    from openwakeword.model import Model
except ImportError:
    sys.exit("pip install openwakeword onnxruntime numpy   (then re-run)")

RATE, CHUNK = 16000, 1280


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != RATE or w.getnchannels() != 1:
            print(
                f"  [skip] {path.name}: needs 16kHz mono "
                f"(got {w.getframerate()}Hz/{w.getnchannels()}ch)"
            )
            return np.array([], dtype=np.int16)
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def peak_score(model: Model, audio: np.ndarray) -> float:
    model.reset()
    peak = 0.0
    for i in range(0, len(audio) - CHUNK + 1, CHUNK):
        pred = model.predict(audio[i : i + CHUNK])
        peak = max(peak, max(pred.values(), default=0.0))
    return peak


def dataset_mode(model_path: str, data_dir: Path):
    try:
        model = Model(wakeword_models=[model_path], inference_framework="onnx")
    except TypeError:
        model = Model(wakeword_model_paths=[model_path])
    print(f"Model loads: PASS ({model_path})\n")
    pos = sorted((data_dir / "positive").glob("*.wav"))
    neg = sorted((data_dir / "negative").glob("*.wav"))
    if not pos and not neg:
        sys.exit(
            f"No WAVs under {data_dir}/positive or /negative — "
            "record them with record_dataset.py first."
        )
    pos_scores, neg_scores = [], []
    print(f"Scoring {len(pos)} positives...")
    for p in pos:
        a = load_wav(p)
        if a.size:
            s = peak_score(model, a)
            pos_scores.append((p.name, s))
            print(f"  {p.name}: {s:.2f}")
    print(f"Scoring {len(neg)} negatives...")
    for p in neg:
        a = load_wav(p)
        if a.size:
            s = peak_score(model, a)
            neg_scores.append((p.name, s))
            if s > 0.3:
                print(f"  {p.name}: {s:.2f}  <-- watch this one")
    print("\nThreshold sweep (hits = positives caught, FPs = negatives fired):")
    print("  thr   hits          FPs")
    best = None
    for t in [x / 100 for x in range(30, 91, 5)]:
        hits = sum(1 for _, s in pos_scores if s >= t)
        fps = sum(1 for _, s in neg_scores if s >= t)
        print(f"  {t:.2f}  {hits}/{len(pos_scores):<12} {fps}/{len(neg_scores)}")
        if fps == 0 and (best is None or hits > best[1]):
            best = (t, hits)
    print()
    if not pos_scores:
        print("VERDICT: NOT TESTABLE — no positive clips.")
    elif best is None:
        print(
            "VERDICT: FAIL — every threshold fires on your negatives. "
            "Retrain with more/better data (especially similar phrases)."
        )
    elif best[1] < len(pos_scores) * 0.8:
        print(
            f"VERDICT: WEAK — at the cleanest threshold ({best[0]:.2f}) it "
            f"catches only {best[1]}/{len(pos_scores)} positives. "
            "Retrain with more varied positives before installing."
        )
    else:
        print(
            f"VERDICT: PASS on this dataset — suggested "
            f"WAKEWORD_THRESHOLD={best[0]:.2f} "
            f"({best[1]}/{len(pos_scores)} positives, 0 false positives). "
            "This is dataset validation only; live-room testing on the "
            "Pi (--live) is still required before calling it complete."
        )


def live_mode(model_path: str):
    import pyaudio

    try:
        model = Model(wakeword_models=[model_path], inference_framework="onnx")
    except TypeError:
        model = Model(wakeword_model_paths=[model_path])
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK
    )
    print(
        "LIVE — speak 'Hey ATOM', try similar phrases, play the TV. "
        "Scores >= your threshold would trigger. Ctrl+C to stop."
    )
    try:
        bar_last = 0
        while True:
            frame = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            s = max(model.predict(frame).values(), default=0.0)
            if s > 0.1 or bar_last > 0.1:
                print(f"  score {s:.2f} {'#' * int(s * 40)}")
            bar_last = s
    except KeyboardInterrupt:
        print("\nDone.")
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("model", help="path to hey_atom.onnx")
    ap.add_argument("--data", type=Path, default=Path(__file__).parent / "data")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    if not Path(a.model).exists():
        sys.exit(
            f"Model not found: {a.model} — train it first "
            "(wakeword/README.md). This tool does not fabricate models."
        )
    live_mode(a.model) if a.live else dataset_mode(a.model, a.data)
