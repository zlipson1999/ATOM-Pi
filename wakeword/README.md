# "Hey ATOM" Wake-Word Pipeline
 
This folder makes producing the real `hey_atom.onnx` a mechanical
task. Nothing here fabricates a model: the file is created by actual
training, then proven by actual validation, then tested on the actual
Pi. Until all three happen, the wake word is NOT ready — the
installer says so and ATOM's mic button carries voice in the
meantime.
 
## The engine (inspected, not assumed)
 
ATOM-Pi's listener uses **openWakeWord** with the **ONNX runtime**:
16 kHz mono 16-bit audio in 1280-sample (80 ms) frames, model loaded
from a file path (`WAKEWORD_MODEL` in `.env`, default
`~/pocket-ai/hey_atom.onnx`), detection threshold `WAKEWORD_THRESHOLD`
(alias `WAKE_THRESHOLD`), cooldown `WAKEWORD_COOLDOWN` (alias
`WAKE_COOLDOWN`), barge-in threshold `WAKE_THRESHOLD_BARGE`. The
model you train must be an openWakeWord classifier exported to ONNX —
which is exactly what the official training notebook produces.
Precedent: be-more-agent ships its own custom openWakeWord model,
proving this exact path on this exact engine.
 
## Route A — Colab training (recommended, no GPU of your own)
 
Training does NOT happen on the Pi. It needs a machine with a GPU;
Google Colab provides one free.
 
1. Open **github.com/dscripka/openWakeWord** → README → *"training
   new models"* → open the **automatic model training notebook** in
   Colab.
2. Set the target phrase to: `hey atom`
3. Run all cells. The notebook synthesizes thousands of positive
   samples with many voices (piper-sample-generator), mixes them with
   large negative/background datasets, trains, and **exports ONNX**.
   How long, and how good the first result is, depends on the run —
   treat it as iterative, not fixed-duration.
4. Download the exported model and rename it `hey_atom.onnx` if
   needed.
5. Optional but recommended: upload your real recordings from
   `record_dataset.py` (at the repo root) where the notebook accepts custom
   positive/negative data — real-room samples measurably improve
   robustness for YOUR mic and YOUR voice.
## Route B — local training (advanced, NVIDIA GPU machine)
 
Clone openWakeWord on a Linux PC with an NVIDIA GPU, install its
training extras, and run the same notebook locally with Jupyter.
Expect multi-GB downloads (negative-feature datasets and augmentation
audio from Hugging Face) — this is why the Pi is not the training
machine.
 
## Then: validate BEFORE installing
 
On the machine holding the model + your recorded dataset, from the repository root:
 
    pip install openwakeword onnxruntime numpy
    python validate_model.py hey_atom.onnx --data data/
 
This replays every recorded clip through the model exactly as the
listener would, sweeps thresholds, and reports: positives caught,
negatives falsely triggered, and the suggested `WAKEWORD_THRESHOLD`.
A model that fails here does not go on the Pi — go back to training
with more/better data.
 
## Install on the Pi
 
Copy `hey_atom.onnx` to `~/pocket-ai/hey_atom.onnx`, or put it in the
atom-pi repo root and run `bash install.sh --sync` (seconds — no
downloads). Put the validated threshold in `.env` as
`WAKEWORD_THRESHOLD`. Then reboot, and run the REAL test — live, in
the robot's actual room, on its actual mic:
 
    cd ~/pocket-ai && source .venv/bin/activate
    python wakeword_validate.py hey_atom.onnx --live
 
(`wakeword_validate.py` is this repo's `validate_model.py`; the
installer renames it when copying it to `~/pocket-ai`. Running from a
repo checkout instead, the file is `validate_model.py`.)
 
Speak "Hey ATOM" at various distances/volumes; watch live scores;
have the TV on; let ATOM talk over it. VALIDATION.md Phase 2 is the
recording sheet. Only after that phase passes is "Hey ATOM" complete
— a model that loads is not a model that works.
 

