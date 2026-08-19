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
   install.sh). Every patch in `patches/apply_patches.py` was
   verified against exactly those commits. If a patch prints a
   manual-fallback warning, apply that specific fallback — do not
   re-clone upstream main to "fix" it.
3. **Never fabricate `hey_atom.onnx`.** No dummy, empty, renamed, or
   placeholder model files, ever. If it's absent, the wake word is
   simply OFF (the mic button works) until the human trains it via
   `wakeword/README.md`. Presence of the file is NOT readiness —
   physical mic validation (VALIDATION.md Phase 2) still applies.
4. **Diagnostics:** `python atom_doctor.py` (and `--logs`,
   `--version`, `--sound`, `--mic`). Read `~/atom-pi-install.log`
   before guessing at failures.
5. **The hardware gate is human work.** VALIDATION.md's phases
   require speaking, listening, and watching the robot. Prepare and
   verify what you can from the terminal; hand the physical steps to
   the human explicitly rather than marking them done.
6. **Honesty over completion.** Never claim a subsystem works
   without evidence from this machine. DEGRADED with a clear note
   beats a false READY.

## Layout

- `install.sh` — staged installer (the only supported install path)
- `patches/apply_patches.py` — verified edits applied to pocket-ai
- `merged/` — ATOM-owned modules (wake listener, vision tool,
  knowledge library, robot components, doctor, personality)
- `wakeword/` — the Hey ATOM training pipeline (recorder, validator)
- `VALIDATION.md` — the hardware acceptance worksheet
- App lives at `~/pocket-ai` after install; config in its `.env`
