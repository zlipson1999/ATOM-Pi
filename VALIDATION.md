# ATOM-Pi — HARDWARE VALIDATION WORKSHEET

This is the final gate. Everything here happens on the real hardware,
by hand. Record results as you go — PASS / FAIL / NOT TESTED, plus
the measured numbers where asked. Nothing in this file is pre-filled,
because none of it has been physically validated yet.

Status rules (use exactly these):
- READY FOR HARDWARE TESTING — software complete, physical validation
  not yet done. (This is the current status.)
- READY — only after Phase 5 (Golden Path) and Phases 1–4, 6–7 pass
  on the physical build.
- NOT READY — REQUIRES FIXES — any blocking implementation failure
  found during validation. Bring the failing output back for a fix.

---

## Phase 0 — Create and install the wake model (BLOCKING)

The wake phrase "Hey ATOM" requires a trained model file. How long
training and tuning take depends on results — plan for iteration, not
a fixed duration.

1. Follow `wakeword/README.md` — the complete pipeline. Short form:
   record a real dataset (`python record_dataset.py`), train
   via openWakeWord's Colab notebook (phrase: `hey atom`), then
   validate offline BEFORE installing:
   `python validate_model.py hey_atom.onnx --data data`
   — it must reach a PASS verdict and it suggests your
   `WAKEWORD_THRESHOLD`.
2. Install: drag `hey_atom.onnx` into the atom-pi repo and re-run the
   installer, OR copy it to `~/pocket-ai/hey_atom.onnx`. Put the
   suggested threshold in `.env`.
4. Verify it loads:
   ```
   cd ~/pocket-ai && source .venv/bin/activate && python wakeword_listener.py
   ```
   Expected: `Wake model loaded — say: 'hey atom'` and
   `Listening for wake word...`
   If instead you see the missing-model message, the file isn't where
   the listener looks — check the path.

| Check | Result |
|---|---|
| hey_atom.onnx exists on the Pi | |
| Model loads (message above) | |

---

## Phase 1 — Bench check (everything enumerated, nothing assumed)

```
cd ~/pocket-ai && source .venv/bin/activate && python atom_doctor.py
```

Copy the doctor's table here. Every row must be OK before the Golden
Path attempt; DEGRADED rows must be understood (e.g. no library drive
attached yet is fine at this stage).

| Doctor row | Status | Note |
|---|---|---|
| Raspberry Pi | | |
| Cooling/power | | |
| Boot drive (NVMe) | | |
| Hailo | | |
| Microphone | | |
| Speaker | | |
| Wake model | | |
| Voice model | | |
| Brain model | | |
| Vision (Moondream) | | |
| Backend | | |
| Internet | | |
| Local library | | |

Calibration (do both, confirm by ear):
```
python atom_doctor.py --sound     # you must hear the test voice
python atom_doctor.py --mic      # your 3s recording must play back clearly
```

Touchscreen: tap targets in the GUI respond; camera preview appears
in the Camera tab.

---

## Phase 2 — Wake reliability (the intended room, real distances)

Environment: the room where ATOM will actually live, normal ambient
noise.

1. Ten trials, ~2 meters from the mic, normal voice: say "Hey ATOM",
   wait for the chime, note hit or miss.
2. Thirty minutes idle with the room's normal sounds (TV off/on as
   realistic): count false triggers.
3. During TTS: ask a long question, and while ATOM speaks, stay
   silent — count self-triggers.

| Measure | Target sense | Result |
|---|---|---|
| Hits out of 10 at 2m | most or all | /10 |
| False triggers in 30 min idle | rare | |
| Self-triggers during TTS | none/rare | |

Live scoring tool for this phase (watch real-time scores while you
speak, play TV, and let ATOM talk):
```
python wakeword_validate.py hey_atom.onnx --live
```
Tuning knobs in `~/pocket-ai/.env` (restart after changing):
`WAKEWORD_THRESHOLD` (raise toward 0.7 for false triggers, lower toward
0.4 for misses), `WAKE_THRESHOLD_BARGE` (self-triggers during
speech), `BARGE_IN=0` (disable in-speech listening entirely). If no
threshold satisfies both directions, the model needs retraining with
more/better samples — that's a Phase 0 loop, not a code fix.

---

## Phase 3 — USB knowledge library (content stays on the drive)

Attach the multi-terabyte drive with your `atom-library` folder
(ZIMs and/or PDFs/EPUBs/TXT).

```
python atom_knowledge.py --status      # must show the drive path + counts
python atom_knowledge.py --index      # first run may take a long time on big collections
python atom_knowledge.py "raspberry pi"
```

Then by voice: "Hey ATOM, what does my library say about Raspberry
Pi?" and "Hey ATOM, compare my local library with what's online."

| Check | Result | Measured |
|---|---|---|
| Drive detected + mounted | | path: |
| ZIMs detected | | count: |
| Indexing completes | | duration: |
| search_library answers with real titles/paths | | latency: s |
| compare_sources returns BOTH labeled sections | | latency: s |
| Unplug mid-session → friendly "library offline" answer, assistant keeps working | | |
| Replug → next library question works without re-indexing | | |
| Library content still only on the USB drive (Pi holds only `library_index/`) | | |

---

## Phase 4 — Internet capability and failure

By voice: "Hey ATOM, what's the weather today?" — must be a real
current answer, and the robot must show its searching state first.

Then pull the network (unplug ethernet / disable WiFi):
- A local question (a joke, a math question) still works.
- A web question gets an honest failure sentence, not a hang or a
  made-up answer.

Restore the network: the same web question now succeeds without a
restart.

| Check | Result |
|---|---|
| Live weather answer | |
| Offline: local capability continues | |
| Offline: web question fails honestly | |
| Recovery without restart | |

---

## Phase 5 — GOLDEN PATH (the acceptance test)

Cold start: power on and touch nothing.

Watch for, in order — every item must be visibly true:

1. Self-check table appears during startup
2. Full robot on screen, idle breathing, core pulsing calmly
3. Say **"Hey ATOM"** → chime → LISTENING (eyes widen, camera chip live)
4. Ask: **"What do you see?"**
5. SEEING — eyes scan
6. THINKING — the right hand VISIBLY travels to the head, makes
   contact, taps with recoil (not just "the arm moved")
7. Reasoning ends → the arm glides back down BEFORE/AS speech starts
8. SPEAKING — answer in the British voice, mouth grille animating,
   core reacting — and the answer describes what the camera actually
   sees, with uncertainty phrasing if unsure
9. Return to idle

| Step | PASS/FAIL | Notes |
|---|---|---|
| Self-check on boot | | |
| Idle robot | | |
| Wake → listening | | |
| Seeing state | | |
| Hand reaches head + taps + recoils | | |
| Arm returns on completion | | |
| Speaking + mouth + core | | |
| Answer matches the real scene | | |
| Back to idle | | |

Repeat once with a library question and once with a web question, and
confirm the robot shows `checking the library…` / `searching the
web…` respectively.

---

## Phase 6 — Barge-in

Ask something that yields a long answer. While ATOM is mid-answer,
say "Hey ATOM" clearly.

| Check | Result |
|---|---|
| Speech stops (within about a sentence) | |
| ATOM goes to LISTENING | |
| The new question gets answered | |
| Mic not left locked (a third exchange works) | |

If it self-triggers or never hears you, tune per Phase 2; `BARGE_IN=0`
is the honest fallback.

---

## Phase 7 — Thermal and stability (sustained)

Run 20+ minutes of mixed load: conversation, a thinking question,
camera detection on, two vision questions, one library search. In a
second terminal:

```
watch -n 5 'vcgencmd measure_temp && vcgencmd get_throttled'
```

| Measure | Result |
|---|---|
| Peak temperature | °C |
| get_throttled stayed 0x0 | |
| Any subsystem crash (watchdog restarts in the terminal) | |
| GUI stayed responsive | |

`throttled != 0x0` means more airflow before any enclosure work.
Watchdog restart lines are recoveries, not passes — note what died
and bring the log tail (`python atom_doctor.py --logs`).

---

## Final decision

All phases PASS → status is **READY**, and the enclosure phase can
begin. Any blocking failure → **NOT READY — REQUIRES FIXES**: record
exactly what failed, run `python atom_doctor.py --logs`, and bring
both back for the fix. Partial completion stays **READY FOR HARDWARE
TESTING** with this worksheet showing precisely what remains.