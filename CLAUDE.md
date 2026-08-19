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
   `install.sh`). Every patch in `patches/apply_patches.py` was verified
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

## Layout

- `install.sh` — staged installer (the only supported install path)
- `patches/apply_patches.py` — verified edits applied to pocket-ai
- `merged/` — ATOM-owned modules (wake listener, vision tool,
  knowledge library, robot components, doctor, personality)
- `wakeword/` — the Hey ATOM training pipeline (recorder, validator)
- `VALIDATION.md` — the hardware acceptance worksheet
- App lives at `~/pocket-ai` after install; config in its `.env`
