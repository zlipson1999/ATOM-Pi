#!/usr/bin/env python3
"""
record_dataset.py — guided recorder for the "Hey ATOM" dataset.

Run on any computer with a microphone (the Pi works too; the machine
you'll actually use ATOM with is ideal because it captures YOUR room
and YOUR mic):

    pip install pyaudio numpy
    python record_dataset.py            # guided session (positives + negatives)
    python record_dataset.py --positive 10   # just 10 more positives
    python record_dataset.py --negative 10   # just 10 more negatives

Output: data/positive/pos_NN.wav and data/negative/neg_NN.wav —
16 kHz, mono, 16-bit, exactly what openWakeWord training and
validate_model.py expect. Files never overwrite; numbering continues.
"""
import argparse
import sys
import time
import wave
from pathlib import Path

import numpy as np
import pyaudio

RATE, SECONDS = 16000, 3
DATA = Path(__file__).parent / "data"

POS_PROMPTS = [
    "normal voice, arm's length from the mic",
    "a bit FASTER",
    "a bit SLOWER",
    "QUIETLY, like someone's sleeping",
    "from about 2 meters away",
    "from across the room",
    "turned slightly away from the mic",
    "with the TV or music playing quietly",
    "higher pitch than usual",
    "lower pitch than usual",
]
NEG_PROMPTS = [
    "say: 'hey adam'", "say: 'hey autumn'", "say: 'hey tom'",
    "say: 'atom bomb'", "say: 'a tomb'", "say: 'hey mom'",
    "just say: 'hey'", "just say: 'atom'",
    "read any sentence from your phone aloud",
    "talk normally about your day for the whole clip",
    "stay SILENT (room tone)", "let the TV/music play into the mic",
]


def record_clip(pa, path: Path, seconds=SECONDS):
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=RATE,
                     input=True, frames_per_buffer=1280)
    print("  recording", end="", flush=True)
    frames = []
    for i in range(int(RATE / 1280 * seconds)):
        frames.append(stream.read(1280, exception_on_overflow=False))
        if i % 4 == 0:
            print(".", end="", flush=True)
    stream.stop_stream(); stream.close()
    audio = np.frombuffer(b"".join(frames), dtype=np.int16)
    peak = int(np.abs(audio).max())
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(audio.tobytes())
    quality = "ok" if 1500 < peak < 32000 else (
        "TOO QUIET — move closer or speak up" if peak <= 1500 else
        "CLIPPING — back off the mic")
    print(f" saved {path.name}  (peak {peak}: {quality})")
    return quality == "ok"


def next_index(folder: Path, prefix: str) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    nums = [int(p.stem.split("_")[1]) for p in folder.glob(f"{prefix}_*.wav")
            if p.stem.split("_")[-1].isdigit()]
    return max(nums, default=0) + 1


def session(kind: str, count: int, pa):
    prompts = POS_PROMPTS if kind == "positive" else NEG_PROMPTS
    folder = DATA / kind
    prefix = "pos" if kind == "positive" else "neg"
    i = next_index(folder, prefix)
    print(f"\n=== {kind.upper()} clips: {count} to record, {SECONDS}s each ===")
    if kind == "positive":
        print("You will say exactly: 'Hey ATOM' — once per clip.\n")
    done = 0
    while done < count:
        prompt = prompts[(i - 1) % len(prompts)]
        input(f"[{done + 1}/{count}] {prompt}\n  Press Enter, wait for the dots, then speak: ")
        time.sleep(0.3)
        if record_clip(pa, folder / f"{prefix}_{i:02d}.wav"):
            done += 1; i += 1
        else:
            print("  re-doing that one.")
    print(f"{kind} set now has {len(list(folder.glob('*.wav')))} clips.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--positive", type=int, default=None)
    ap.add_argument("--negative", type=int, default=None)
    a = ap.parse_args()
    pa = pyaudio.PyAudio()
    try:
        if a.positive is None and a.negative is None:
            print("Guided session: 30 positives, then 40 negatives.")
            print("Take breaks any time with Ctrl+C — numbering resumes.")
            session("positive", 30, pa)
            session("negative", 40, pa)
        else:
            if a.positive: session("positive", a.positive, pa)
            if a.negative: session("negative", a.negative, pa)
        print("\nNext: train via wakeword/README.md, then run "
              "validate_model.py against this data.")
    except KeyboardInterrupt:
        print("\nPaused — run again to continue where you left off.")
    finally:
        pa.terminate()


if __name__ == "__main__":
    sys.exit(main())
