# CLAUDE.md — instructions for AI coding agents working in this repo

ATOM-Pi: a local-first AI robot companion for Raspberry Pi 5
(pocket-ai chassis + wake word, full-body robot GUI, Moondream vision,
USB knowledge library). The human building this is new to hardware
projects — explain what you're doing in plain language as you go.

## The rules

1. **install.sh is the installer. Run it; do not rewrite it.**
   It is staged and resumable via `~/.atom-pi-stage`. It reboots the
   Pi at stages 0 and 2 — after each reboot, run `bash install.sh`
   again and it continues. Fix failures minimally and re-run; do not
   invent an alternative install path.

2. **Do not unpin the upstream commits** (`POCKET_SHA`, `BMA_SHA` in
   `install.sh`). Every patch in `apply_patches.py` (repo root) was verified
   against exactly those commits. If a patch prints a manual-fallback
   warning, apply that specific fallback — do not re-clone upstream
   main to "fix" it.

3. **Never fabricate `hey_atom.onnx`.**
   No dummy, empty, renamed, or placeholder model files, ever. If it's
   absent, the wake word is simply OFF (the mic button works) until the
   human trains it via `wakeword/README.md`. Presence of the file is
   NOT readiness — physical mic validation (`VALIDATION.md` Phase 2)
   still applies.

4. **Diagnostics:** `python atom_doctor.py` (and `--logs`,
   `--version`, `--sound`, `--mic`). Read `~/atom-pi-install.log`
   before guessing at failures.

5. **The hardware gate is human work.**
   `VALIDATION.md`'s phases require speaking, listening, and watching
   the robot. Prepare and verify what you can from the terminal; hand
   the physical steps to the human explicitly rather than marking
   them done.

6. **Honesty over completion.**
   Never claim a subsystem works without evidence from the current
   environment. Evidence must match the claim: code compilation does
   not prove hardware functionality, simulation does not prove physical
   functionality, and documentation does not prove execution.
   **DEGRADED** with a clear note beats a false **READY**.

7. **Source of truth.**
   When sources disagree, use this order of authority:

   actual tested ATOM-Pi code
   > pinned upstream implementation
   > repository documentation
   > README/build-guide assumptions

   Do not spend time endlessly reconciling contradictory documentation
   when executable behavior establishes the truth.

8. **No speculative feature creep.**
   Do not add capabilities simply because they are technically
   interesting. Complete, integrate, test, and harden the defined
   ATOM-Pi experience before adding optional features. Prefer the
   simplest architecture that reliably satisfies the requirements.

9. **Work from evidence.**
   Before changing code, inspect the existing implementation and
   reproduce the problem where possible. Make the smallest correct
   change that fixes the verified problem. After changes, run the
   relevant tests, compilation checks, diagnostics, or other
   appropriate validation. Report exactly what was verified.

10. **Do not redesign completed systems.**
    If a subsystem is documented as implemented and no actual defect
    has been demonstrated, preserve it. Do not replace working
    components merely because another architecture appears cleaner,
    newer, or technically interesting. Do not redesign unrelated
    subsystems while completing a specific task.

11. **Completion discipline.**
    A task is complete only when its acceptance criteria are satisfied.
    Do not mark hardware-dependent requirements PASS from simulation,
    documentation, compilation, or static inspection.

    Use:

    **READY FOR HARDWARE TESTING**

    when the software is prepared but physical validation remains.

    Use:

    **READY**

    only when the required physical acceptance tests have actually
    passed.

    Use:

    **NOT READY — REQUIRES FIXES**

    when an implementation defect or unresolved blocker remains.

## Operating mode

When given a task:

1. Read `CLAUDE.md` first.
2. Inspect the existing repository and relevant documentation before
   making changes.
3. Determine whether the task is implementation, bug fix, validation,
   documentation, or hardware-only.
4. Do not redesign unrelated systems.
5. Implement the smallest correct change.
6. Test everything that can be tested on the current machine.
7. Clearly identify anything requiring physical hardware or human
   action.
8. Never claim a physical test passed unless it was actually performed.
9. At the end of the task, report:
   - what changed
   - what was tested
   - what passed
   - what could not be tested
   - remaining blockers
   - exact next human action, if any
## ATOM-Pi mission

The goal of this repository is to produce a working ATOM-Pi system, not merely
a successful software installation.

The completed experience is:

- local-first AI with internet access when needed
- full-body ATOM robot UI, not only a face
- voice-first, hands-free interaction
- wake word when the real model is trained and physically validated
- camera vision when required
- local AI reasoning
- speech output
- visible thinking behavior, including the arm raising and hand tapping the head
  while ATOM is genuinely processing
- persistent ATOM visual identity across all states
- optional external USB knowledge library, including Kiwix content
- normal Raspberry Pi desktop access when the user needs it
- clear system status and diagnostics
- graceful degradation when hardware, internet, or the USB library is unavailable

The existing architecture and pinned upstream components should be preserved
unless a verified defect requires a change.

The objective is to finish, integrate, test, and harden this experience.

Do not replace a working subsystem merely to make the code more elegant,
modern, abstract, or technically interesting.

Do not declare ATOM-Pi READY until the required physical validation has actually
been performed.

## Layout

- `install.sh` — staged installer (the only supported install path)
- `apply_patches.py` — verified edits applied to pocket-ai (repo root)
- ATOM-owned modules at the repo root: wakeword_listener.py,
  vision_describe.py, atom_knowledge.py, atom_doctor.py,
  AtomRobot.jsx, AtomRobotAdapter.jsx, personality.txt,
  record_dataset.py, validate_model.py
  (install.sh also accepts the canonical merged/ + patches/ +
  wakeword/ layout — its resolver checks both)
- `wakeword/` — Hey ATOM training docs (README.md pipeline guide,
  DATASET.md data spec); the recorder/validator tools are at root
- `VALIDATION.md` — the hardware acceptance worksheet
- App lives at `~/pocket-ai` after install; config in its `.env`
