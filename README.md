# ATOM-Pi

**One fully local AI robot companion on a Raspberry Pi 5 — one install
command.** Wake word, voice conversation, real-time camera detection,
scene understanding, and a full-body animated robot with a pulsing
chest core that taps its head while it thinks.

Built by integrating two open-source projects, audited at source level:

- [nazirlouis/pocket-ai](https://github.com/nazirlouis/pocket-ai) —
  the chassis: FastAPI backend, WebSocket voice pipeline, Electron
  touchscreen GUI, semantic router, tools, task scheduler, Hailo
  camera pipeline
- [brenpoly/be-more-agent](https://github.com/brenpoly/be-more-agent)
  — the proven concepts: openWakeWord wake word (incl. custom-model
  path), Moondream visual reasoning, feedback sounds,
  hardware-aware audio

ATOM = EARS (wake word + Whisper) + EYES (Hailo detection + Moondream
reasoning) + BRAIN (Qwen3-4B, thinking/fast routing) + MOUTH (Piper,
British voice) + FACE (full-body code-drawn robot, real-state driven).

## The wake phrase is "Hey ATOM" — one setup step, read this first

Wake phrases are trained neural models, not strings in code, and no
pretrained "Hey ATOM" model exists — so this repo expects a file
named **`hey_atom.onnx`**, and you create it once, free, yourself
(be-more-agent ships its own custom `wakeword.onnx`, which is proof
this exact path works). Budget an evening: recording the dataset takes
roughly half an hour, training runs unattended, and how many rounds of
retrain-and-validate you need depends on your results:

The complete pipeline is documented in **`wakeword/README.md`**, with
the tools at the repo root — a guided dataset recorder
(`record_dataset.py`), the training routes (openWakeWord's Colab notebook — free
GPU, no install — or a local NVIDIA machine), and a validator that
replays your recordings through the model exactly as the listener
will and suggests your threshold. Validate before installing where you
can — but you do **not** have to have the model before you build. If
ATOM is already installed, put the passing `hey_atom.onnx` in this
repo and run `bash install.sh --sync` (fast: no downloads, no apt),
or just `cp hey_atom.onnx ~/pocket-ai/ && sudo reboot`.

**Until the file exists, the wake word is simply off** — the listener
says so and exits, nothing pretends to work, and the touchscreen mic
button drives voice conversations exactly as normal. There is no
fallback phrase.

## Hardware

| Part | Class | Notes |
|---|---|---|
| Raspberry Pi 5, 16GB | REQUIRED | 8GB works; 16GB is comfortable |
| Official 27W USB-C supply | REQUIRED | phone chargers cause random resets |
| Active cooler | REQUIRED | sustained LLM load throttles a bare board |
| microSD 32GB (A2) | REQUIRED | first boot only, then migrate |
| NVMe SSD M.2 2280, 500GB | REQUIRED | the installer gates on it (Stage 1); models load far faster than SD |
| Dual M.2 PCIe-switch HAT (ASM2806) | REQUIRED | only way to run SSD + Hailo together |
| Hailo-8L **M.2 module, key B+M** | REQUIRED | the installer gates on it (Stage 1); real-time detection off-CPU |
| Camera Module 3 + Pi 5 22-pin cable | RECOMMENDED | camera ships with the wrong cable |
| USB microphone | REQUIRED | wake word + speech |
| Raspberry Pi Touch Display 2, 10" | RECOMMENDED | official; DSI + GPIO power — powered from the Pi, no second supply; Pi 5 only; Pi mounts on back |
| Small USB speaker | REQUIRED | the Touch Display 2 has no audio — this is ATOM's voice |
| M2.5 standoff kit | RECOMMENDED | the M.2 HAT sits between Pi and display, so the included screws are too short |
| USB knowledge-library drive (any size, multi-TB fine) | OPTIONAL | content stays on the drive; only a compact index lives on the Pi |
| Raspberry Pi **AI HAT+** | DO NOT BUY | blocks the SSD slot — get the bare M.2 module |
| Skimping on the 27W official supply | DO NOT | the Pi now powers the display too; phone chargers cause resets |

**The installer will not proceed without the Hailo module and the NVMe
drive** — Stage 1 checks for both on PCIe and stops if either is
missing. At *runtime* the software does degrade gracefully (Hailo
absent -> voice, chat, and Moondream still work; camera absent -> ATOM
says it can't see rather than pretending), but that is the fallback
behavior after a complete install, not a supported way to build. If
you want to bring up partial hardware anyway, re-run with
`ATOM_SKIP_PCIE_CHECK=1` — untested, and Stage 2 still installs the
Hailo stack.

## Install

1. Flash **Raspberry Pi OS (64-bit, Desktop)** with Raspberry Pi
   Imager (set username, WiFi, enable SSH in its settings).
2. Boot, open a terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/zlipson1999/ATOM-Pi/main/install.sh | bash
```

3. **When it reboots, run the same command again** — progress is kept
   in `~/.atom-pi-stage`:

```
run  -> OS + firmware update, reboot
run  -> PCIe Gen3, reboot
run  -> gate: BOTH Hailo and NVMe must appear on the bus
        (one manual step: SD->SSD migration via SD Card Copier)
run  -> everything: Hailo stack, pocket-ai clone, Python env,
        .env (audio device auto-detected, Qwen3-4B configured),
        voice, Ollama+Moondream, sounds, verified patches, GUI build,
        autostart
```

4. Reboot once more. ATOM starts itself; first launch finishes its
   model downloads, then say **"Hey ATOM"**.

## What the merge actually changes (all anchors verified in source)

| Change | Mechanism |
|---|---|
| Brain -> Qwen3-4B Q4_K_M | `.env`: `CHAT_REPO_ID` / `CHAT_FILENAME` (backend auto-downloads) |
| Audio output | `.env`: `TTS_ALSA_DEVICE` (auto-detected: USB speaker first — the DSI display has no audio — HDMI fallback) |
| British voice | `chat_ai.py`: `PocketAudio(model_name="en_GB-alan-medium")`, files pre-placed in `models/` |
| ATOM personality | both hardcoded system prompts -> `personality.txt` |
| Wake word ears | `wakeword_listener.py`: openWakeWord -> `{"type":"toggle_voice"}` on the real `/ws/voice`; releases the mic to Whisper; re-arms only after backend reports `idle` (no self-triggering) |
| Camera on voice chat | listener POSTs `/camera/start` on wake |
| Visual reasoning | `describe_scene` runner appended to `tool_ai.py`'s `TOOL_RUNNERS`; schema in `tools.json`; scene questions added to the router's tool route; Moondream via Ollama |
| Local USB library | ATOM-owned `atom_knowledge.py` (not a patch): Kiwix via `kiwix-serve`, documents via a local FTS index; `search_library` + `compare_sources` tools |
| Full-body robot GUI | `Home.jsx` already renders its avatar from the backend's `voice_status` events — one verified import swap routes that real state into `AtomRobot.jsx` |
| ATOM hub | `Home.jsx`: title becomes ATOM and the menu becomes VOICE / CHAT / VISION / LIBRARY, with DESKTOP set apart below (it leaves ATOM rather than doing something with it) |
| VOICE tile | calls the backend's existing `toggleVoice()` — the same action tapping the robot already performs, made discoverable. Works without a wake model |
| LIBRARY screen | ATOM-owned `AtomLibrary.jsx` + `atom_library_api.py` (a FastAPI router mounted on `app.py`): `/library/status`, `/library/search`, `/library/index`. Puts the USB library on the touchscreen instead of only in chat |
| DESKTOP tile | `preload` exposes `desktopMode()`; the main process spawns `atom-stop.sh` detached, freeing the Pi for normal desktop use |

## The robot

Code-drawn, offline, original design (sparring-robot spirit — not a
reproduction of any copyrighted character). Full head, glowing visor
eyes, mouth grille, neck, shoulders, torso, two arms with hands, and
a prominent pulsing chest power core. States: boot, idle (breathing),
listening, **thinking (right arm raises and taps the head —
interruptible: every pose is a CSS transform transition, so if
reasoning finishes early the arm glides back down mid-gesture)**,
seeing (eye scan), tool_use, speaking (grille animates), error,
offline. It renders only states the backend actually reports.

## The interaction contract (the acceptance test)

ATOM-Pi is complete only when this works as ONE interaction, on real
hardware: say "Hey ATOM" -> chime, camera indicator on -> robot goes
attentive -> you speak -> (a library or web question first shows its own searching state) -> robot's hand visibly travels to its head,
makes contact, taps, recoils -> (eyes scan if the question needs
vision) -> hand glides back down -> ATOM answers in the British voice
while the mouth grille animates and the core reacts -> robot returns
to idle breathing. If you speak "Hey ATOM" over it mid-answer, it
stops within a sentence and listens again. Individual subsystems
passing does not count; this sequence does.

## Barge-in (interrupting ATOM)

Say the wake phrase while ATOM is speaking and it stops within a
sentence: the listener keeps the mic open during speech at a raised
threshold (`WAKE_THRESHOLD_BARGE`, default 0.7), sends `abort`, and
the backend both halts generation and clears the TTS queue (verified
patch — `clear_queue()` exists in the real TTS engine; the sentence
already playing finishes, which is why "within a sentence"). Echo
caveat: if the mic sits right against the speaker, self-triggering is
possible — set `BARGE_IN=0` in `.env` to return to strict
mic-handoff mode.

## State priority & animation rules

One resolver (in `AtomRobotAdapter.jsx`) owns the body:
`error > boot > speaking > thinking > seeing > knowledge_search >
web_search > tool_use > listening > idle`, offline when the backend is gone. Every pose is a transform
transition and every repeating motion is cleared on state change, so
thinking->speaking lowers the arm mid-gesture, speaking->listening
stops the mouth instantly, and any->error cancels everything. The
robot renders only states the backend actually reported — the voice
path now emits real `seeing` / `knowledge_search` / `web_search` /
`tool_use` statuses when a vision or
tool request is what's happening (verified patch).

## Local-first + internet-capable (the accurate description)

ATOM is **local-first, not offline-only** — an earlier draft of this
document overstated that, and the verified code disagrees, so the
code wins: the brain, ears (wake + Whisper), eyes (Hailo + Moondream),
and voice all run on the Pi, AND the tool layer reaches the internet
when a question needs it (web search, weather, stock prices — these
exist in the verified upstream code and are kept). The router sends
each request to the right source: local reasoning, the camera, the
web, or the local USB library — and `compare_sources` combines the
library and the web with both labeled.

## Privacy (what actually leaves the device)

Camera frames, microphone audio, and transcripts never leave the Pi —
vision runs on Moondream locally, speech on Whisper locally. What CAN
leave: when a web tool runs, the search/weather/stock **query text**
goes to those public web APIs, exactly as in upstream pocket-ai. The
local library never leaves the device — retrieval and reasoning over
it are fully local. Frames are captured only on wake
(`CAMERA_ON_WAKE=0` disables) or vision questions, land in
`~/pocket-ai/captures/`, and are deletable from the gallery. Honest
physical shutter: a lens cover.

## Local knowledge library (USB drive)

The library is entirely optional — ATOM runs fully without it. To use it, plug in any USB drive — multi-terabyte is fine — holding Kiwix `.zim`
files and/or documents (PDF, EPUB, TXT, MD), ideally inside a folder
named `atom-library` (or set `ATOM_LIBRARY_PATH` in `.env`). Content
STAYS on the drive; only a compact search index lives on the Pi.
Kiwix answers come from `kiwix-serve` actually searching your ZIMs;
document answers come from a local full-text index (build/refresh it
with `python atom_knowledge.py --index`). Ask: *"Hey ATOM, what does
my library say about Raspberry Pi?"* or *"compare my local library
with what's online."* Answers carry real titles and paths — and if
nothing was found or the drive is unplugged, ATOM says exactly that.
Unplugging never breaks the assistant; replugging resumes with the
same index.

## Desktop mode (the Pi stays a normal computer)

ATOM runs as an app, not a kiosk — the Raspberry Pi desktop is always
underneath. Two icons live on the desktop: **ATOM** starts everything,
**ATOM — Desktop Mode** suspends the camera, wake word, backend, and
GUI so the Pi's full resources go to browsing, downloads, files,
terminal, and managing the USB library. Double-click ATOM to return.
No reinstall, no reboot required either way.

## Diagnostics, calibration, logs, backup

`python atom_doctor.py` prints a READY/DEGRADED check of every
subsystem (Pi, cooling, NVMe, Hailo, mic, speaker, wake model, voice,
brain, Moondream, backend, disk). First-run calibration: `--sound`
(hear a test tone) and `--mic` (record 3s, play it back). `--logs`
tails the structured backend log (`LOG_FILE=atom.log`, timestamped
per subsystem — pocket-ai's own logging, now switched on). `--backup`
saves your `.env`, personality, wake model, and conversations to a
dated tarball you can restore after a reinstall. `--version` prints
the full version record: ATOM-Pi version, OS, pinned upstream
commits, and every model in use — the reproducibility receipt.

## Watchdog & recovery

The autostart script supervises all three subsystems: if the backend,
the ears, or the GUI exits, it restarts that subsystem in 3 seconds
rather than requiring a reboot. Hard hangs still need the power
button — that's the current honest limit.

## Updates & rollback

Upstreams are **pinned to the exact commits every patch was verified
against** (`POCKET_SHA`, `BMA_SHA` in `install.sh`), so a future
upstream change can't silently break the merge.

**To refresh the ATOM layer** (new wake model, edited module, updated
robot component): `bash install.sh --sync`. This re-copies the ATOM
files and re-applies the patches in seconds — no apt, no model
downloads, no npm. Running `bash install.sh` with no arguments on a
completed install does the same thing.

**To rebuild against a fresh pocket-ai clone:** `rm ~/.atom-pi-stage`
and re-run with `UPDATE=1` — it moves the current install to
`~/pocket-ai.bak-<date>` first, so rollback is moving that folder
back. This is the slow path: it redoes the system upgrade, the Hailo
install, and every model download. To track upstream main instead,
override the SHA env vars and watch the patcher's output for manual
follow-ups.

## Latency budgets (targets — measure on hardware)

These are the feel-targets to validate with a stopwatch on the real
build, not measurements: wake chime near-instant after the phrase;
simple answers begin speaking within a few seconds; thinking answers
show the head-tap within a second of the transcript landing and may
reason 15-20s; vision answers show `seeing` immediately and speak
within ~10-15s (first Moondream call is slower while it loads); TTS
starts on the first generated sentence, not the full reply (the
backend streams sentence-by-sentence — verified). If reality misses
these badly, `atom_doctor.py` plus the throttle check is the first
stop.

## Designed fallbacks

Qwen3-4B unreachable -> delete the `CHAT_*` lines in `.env` and the
stock model loads. Moondream down -> `describe_scene` says so in one
friendly sentence; Hailo detection is unaffected. Hailo absent ->
voice, chat, and Moondream all still work. Wake model absent -> the
listener says so and the touchscreen mic carries voice. No subsystem
pretends.

## Simulation mode (test without hardware)

`atom-live-demo.html` in this repo runs in any desktop browser: the
full robot, every state on buttons, a scripted run of the complete
interaction contract, and your computer's camera and mic. It exists
so the robot, gesture, and flow can be validated before the Pi is
even assembled — and the README says plainly: passing in simulation
is not hardware validation.

The chat brain is **optional and opt-in**. Click the plug button to
paste an Anthropic API key; it is kept in that browser tab only
(`sessionStorage`), never written into the file, and sent only to
Anthropic. Without a key the demo says so and everything else still
works. (An earlier version of this page sent an unauthenticated
request, so the brain never worked and the page merely reported a
connection problem.)

## Customizing

- **Personality:** edit `~/pocket-ai/personality.txt` (keep it short —
  long prompts slow every local response).
- **Voice:** any Piper voice: put `.onnx` + `.onnx.json` in
  `~/pocket-ai/models/` and change the `model_name` in `chat_ai.py`.
- **Wake sensitivity / listen window:** `WAKEWORD_THRESHOLD`,
  `LISTEN_SECONDS` in `.env`.
- **Robot look:** it's one SVG in
  `chat-gui/src/renderer/src/components/AtomRobot.jsx` — colors and
  proportions are constants at the top.

## Troubleshooting

**Installer gate: "Hailo not detected / NVMe not detected"** — power
off; reseat the ribbon (latched, right orientation, both ends),
connect the HAT's supplemental/pogo power, reseat both modules; run
again.

**No sound** — `aplay -l`, put the right card in `.env` as
`TTS_ALSA_DEVICE=plughw:X,0`, restart. If your USB speaker has its
own volume knob, check that too.

**Wake word too eager / deaf** — tune `WAKEWORD_THRESHOLD` (0.4–0.7)
in `.env`. (That exact name — the installer writes `WAKEWORD_THRESHOLD`,
and it takes precedence over the older `WAKE_THRESHOLD` alias, so
editing the alias has no effect.)

**"What do you see" says vision isn't running** —
`sudo systemctl start ollama` and confirm `ollama pull moondream`
finished.

**Start over** — `rm ~/.atom-pi-stage` and run the command again.
Log of everything: `~/atom-pi-install.log`.

## Security notes (plain-spoken)

The one-liner is `curl | bash` — convenient, and it means you're
trusting this repo and the upstreams it clones (pocket-ai,
be-more-agent, Ollama's installer, model downloads from Hugging
Face). For a harder setup: read `install.sh` first (it's commented),
or clone the repo and run `bash install.sh` locally. Upstreams are
pinned to verified commits (`POCKET_SHA`, `BMA_SHA`); override those
env vars to track `main` if you prefer fresh over reproducible. No
secrets are stored anywhere; nothing leaves the device at runtime.

**Network exposure.** Two services listen on the Pi, and both are
bound to localhost on purpose:

- The **backend** (port 8000) serves the chat API and `/captures` —
  the stills ATOM takes when you ask what it sees. Upstream pocket-ai
  binds `0.0.0.0`, which puts those photos on your network with no
  authentication; `apply_patches.py` rebinds it to `127.0.0.1`. Every
  caller is local (the listener, the vision tool, the doctor, the
  Electron GUI on the Pi itself), so nothing is lost. To expose it
  deliberately, set `ATOM_BIND_HOST=0.0.0.0`.
- **kiwix-serve** (port 8090, only when a library drive is attached)
  is started with `--address 127.0.0.1` for the same reason — your
  offline library is yours.

If you put ATOM on a network you don't control, check both with
`ss -tlnp` before trusting them.

## Credits

The heavy lifting is nazirlouis/pocket-ai and the ideas proven in
brenpoly/be-more-agent (MIT). Voices: rhasspy/piper (MIT). Qwen3:
Apache 2.0. Moondream: Apache 2.0. This repo is the integration
layer, the wake-word ears, the vision tool, and the robot.
