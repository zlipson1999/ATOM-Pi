# \# CLAUDE.md — instructions for AI coding agents working in this repo

# 

# ATOM-Pi: a local-first AI robot companion for Raspberry Pi 5

# (pocket-ai chassis + wake word, full-body robot GUI, Moondream vision,

# USB knowledge library). The human building this is new to hardware

# projects — explain what you're doing in plain language as you go.

# 

# \## The rules

# 

# 1\. \*\*install.sh is the installer. Run it; do not rewrite it.\*\*

# &#x20;  It is staged and resumable via `\~/.atom-pi-stage`. It reboots the

# &#x20;  Pi at stages 0 and 2 — after each reboot, run `bash install.sh`

# &#x20;  again and it continues. Fix failures minimally and re-run; do not

# &#x20;  invent an alternative install path.

# 

# 2\. \*\*Do not unpin the upstream commits\*\* (`POCKET\_SHA`, `BMA\_SHA` in

# &#x20;  `install.sh`). Every patch in `patches/apply\_patches.py` was verified

# &#x20;  against exactly those commits. If a patch prints a manual-fallback

# &#x20;  warning, apply that specific fallback — do not re-clone upstream

# &#x20;  main to "fix" it.

# 

# 3\. \*\*Never fabricate `hey\_atom.onnx`.\*\*

# &#x20;  No dummy, empty, renamed, or placeholder model files, ever. If it's

# &#x20;  absent, the wake word is simply OFF (the mic button works) until the

# &#x20;  human trains it via `wakeword/README.md`. Presence of the file is

# &#x20;  NOT readiness — physical mic validation (`VALIDATION.md` Phase 2)

# &#x20;  still applies.

# 

# 4\. \*\*Diagnostics:\*\* `python atom\_doctor.py` (and `--logs`,

# &#x20;  `--version`, `--sound`, `--mic`). Read `\~/atom-pi-install.log`

# &#x20;  before guessing at failures.

# 

# 5\. \*\*The hardware gate is human work.\*\*

# &#x20;  `VALIDATION.md`'s phases require speaking, listening, and watching

# &#x20;  the robot. Prepare and verify what you can from the terminal; hand

# &#x20;  the physical steps to the human explicitly rather than marking

# &#x20;  them done.

# 

# 6\. \*\*Honesty over completion.\*\*

# &#x20;  Never claim a subsystem works without evidence from the current

# &#x20;  environment. Evidence must match the claim: code compilation does

# &#x20;  not prove hardware functionality, simulation does not prove physical

# &#x20;  functionality, and documentation does not prove execution.

# &#x20;  \*\*DEGRADED\*\* with a clear note beats a false \*\*READY\*\*.

# 

# 7\. \*\*Source of truth.\*\*

# &#x20;  When sources disagree, use this order of authority:

# 

# &#x20;  actual tested ATOM-Pi code

# &#x20;  > pinned upstream implementation

# &#x20;  > repository documentation

# &#x20;  > README/build-guide assumptions

# 

# &#x20;  Do not spend time endlessly reconciling contradictory documentation

# &#x20;  when executable behavior establishes the truth.

# 

# 8\. \*\*No speculative feature creep.\*\*

# &#x20;  Do not add capabilities simply because they are technically

# &#x20;  interesting. Complete, integrate, test, and harden the defined

# &#x20;  ATOM-Pi experience before adding optional features. Prefer the

# &#x20;  simplest architecture that reliably satisfies the requirements.

# 

# 9\. \*\*Work from evidence.\*\*

# &#x20;  Before changing code, inspect the existing implementation and

# &#x20;  reproduce the problem where possible. Make the smallest correct

# &#x20;  change that fixes the verified problem. After changes, run the

# &#x20;  relevant tests, compilation checks, diagnostics, or other

# &#x20;  appropriate validation. Report exactly what was verified.

# 

# 10\. \*\*Do not redesign completed systems.\*\*

# &#x20;   If a subsystem is documented as implemented and no actual defect

# &#x20;   has been demonstrated, preserve it. Do not replace working

# &#x20;   components merely because another architecture appears cleaner,

# &#x20;   newer, or technically interesting. Do not redesign unrelated

# &#x20;   subsystems while completing a specific task.

# 

# 11\. \*\*Completion discipline.\*\*

# &#x20;   A task is complete only when its acceptance criteria are satisfied.

# &#x20;   Do not mark hardware-dependent requirements PASS from simulation,

# &#x20;   documentation, compilation, or static inspection.

# 

# &#x20;   Use:

# 

# &#x20;   \*\*READY FOR HARDWARE TESTING\*\*

# 

# &#x20;   when the software is prepared but physical validation remains.

# 

# &#x20;   Use:

# 

# &#x20;   \*\*READY\*\*

# 

# &#x20;   only when the required physical acceptance tests have actually

# &#x20;   passed.

# 

# &#x20;   Use:

# 

# &#x20;   \*\*NOT READY — REQUIRES FIXES\*\*

# 

# &#x20;   when an implementation defect or unresolved blocker remains.

# 

# \## Operating mode

# 

# When given a task:

# 

# 1\. Read `CLAUDE.md` first.

# 2\. Inspect the existing repository and relevant documentation before

# &#x20;  making changes.

# 3\. Determine whether the task is implementation, bug fix, validation,

# &#x20;  documentation, or hardware-only.

# 4\. Do not redesign unrelated systems.

# 5\. Implement the smallest correct change.

# 6\. Test everything that can be tested on the current machine.

# 7\. Clearly identify anything requiring physical hardware or human

# &#x20;  action.

# 8\. Never claim a physical test passed unless it was actually performed.

# 9\. At the end of the task, report:

# &#x20;  - what changed

# &#x20;  - what was tested

# &#x20;  - what passed

# &#x20;  - what could not be tested

# &#x20;  - remaining blockers

# &#x20;  - exact next human action, if any

# 

# \## Layout

# 

# \- `install.sh` — staged installer (the only supported install path)

# \- `patches/apply\_patches.py` — verified edits applied to pocket-ai

# \- `merged/` — ATOM-owned modules (wake listener, vision tool,

# &#x20; knowledge library, robot components, doctor, personality)

# \- `wakeword/` — the Hey ATOM training pipeline (recorder, validator)

# \- `VALIDATION.md` — the hardware acceptance worksheet

# \- App lives at `\~/pocket-ai` after install; config in its `.env`

