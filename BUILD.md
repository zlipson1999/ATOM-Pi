# ATOM-Pi — Solder-Free Build Guide

## 1. What you are building

ATOM-Pi is a Raspberry Pi 5 robot companion with:

- full-body animated robot interface
- voice input/output
- "Hey ATOM" wake word
- camera vision
- Hailo acceleration
- local Qwen brain
- local Moondream vision
- optional USB knowledge library
- internet access when needed
- normal Raspberry Pi desktop access
- physical hardware validation after software installation

The robot's on-screen body is the robot. It is not just a face: head, eyes,
mouth, neck, shoulders, torso, two arms/hands, and chest power core are rendered
together. During thinking, the arm raises and taps the robot's head.

## 2. Parts

- Required
- PartWhat it does
- Raspberry Pi 5 16GBMain computer
- Official 27W USB-C Pi supplyPower
- Active coolerKeeps Pi cool under sustained AI load
- 32GB+ A2 microSDInitial boot
- USB microphoneEars
- Keyboard + mouseInitial setup
- Wi-Fi/EthernetInternet during setup

The README says 8GB can work, but 16GB is the comfortable configuration.

- Recommended for the complete build
- NVMe M.2 2280 500GB
- Dual M.2 PCIe-switch HAT / ASM2806
- Hailo-8L M.2 module, B+M key
- Raspberry Pi Camera Module 3
- correct Pi 5 22-pin camera cable
- Raspberry Pi Touch Display 2, 10 inch (official; powered from the Pi)
- Small USB speaker (the display has no audio — this is ATOM's voice)
- M2.5 standoff kit (the M.2 HAT sits between Pi and display)
- USB knowledge-library drive
- Do NOT buy

Raspberry Pi AI HAT+

The README specifically calls this out because it conflicts with the SSD/Hailo
configuration being used by ATOM-Pi.

## 3. No soldering

You do not need to solder anything for the ATOM-Pi configuration.

The physical build is:

```
Raspberry Pi 5
     │
     ├── Active cooler
     │
     ├── PCIe / M.2 HAT
     │      ├── NVMe SSD
     │      └── Hailo-8L M.2
     │
     ├── Camera cable → Camera Module 3
```

```
     │
     ├── USB → Microphone
     │
     ├── USB → optional library drive
     │
```

     └── Display connection → touchscreen

Use the mechanical instructions supplied with the specific HAT and modules for
inserting/securing the M.2 cards. Do not force an M.2 module into a slot.

## 4. Assemble the Pi while it is OFF

Do not connect power yet.

Step 1 — Pi

Put the Raspberry Pi 5 on a clean, non-conductive surface.

Do not power it.

Step 2 — Cooling

Install the active cooler according to the cooler manufacturer's instructions.

The cooler is required because ATOM-Pi runs sustained local AI workloads.

Step 3 — PCIe/M.2 board

Attach the dual M.2 PCIe-switch HAT to the Pi according to the HAT's supplied
mechanical instructions.

Do not improvise a cable orientation.

Step 4 — NVMe

Install the NVMe M.2 2280 SSD into the appropriate M.2 slot.

Secure it with the supplied retaining hardware.

Step 5 — Hailo

Install the Hailo-8L M.2 B+M-key module into its designated M.2 slot.

Secure it.

The ATOM-Pi installer specifically expects both Hailo and NVMe to appear on
PCIe.

Step 6 — Camera

Connect the Camera Module 3 using the Pi 5 22-pin cable, into the MIPI
port labeled 0. (The display takes the port labeled 1 in Step 9.)

The README specifically warns that the camera ships with the wrong cable for
this setup.

Step 7 — Microphone

Plug the USB microphone into USB.

Step 8 — Optional library

If you are using your large USB library drive, connect it to USB.

Do not copy your entire Kiwix library onto the Pi.

ATOM-Pi's library design keeps the content on the external drive and keeps only
a compact search index locally.

Step 9 — Screen and speaker

The official Raspberry Pi Touch Display 2 (10 inch) is powered BY the Pi —
that is correct and intended. There is no second wall plug for the screen.

Two connections, both cables included in the display's box:

```bash
# 1. DSI ribbon: display's DSI port -> one of the Pi 5's two 22-pin MIPI ports
#    Use the port labeled 1 (the camera has port 0) — both ports are now in use
# 2. GPIO power cable: display's power port -> Pi header pins 2, 4, 6
```

Mounting: the Pi normally screws straight onto the display's back with the
included M2.5 screws — but in this build the Seeed M.2 HAT sits underneath
the Pi, so use longer M2.5 standoffs to raise the Pi+HAT stack off the
display board. The Active Cooler faces outward, away from the display.

The display panel is portrait-native (1200x1920). On first boot, open
Screen Configuration and rotate it to landscape.

Plug the small USB speaker into any USB-A port. During setup, the mic,
speaker, keyboard, and mouse fill all four USB ports — that's fine; the
optional library drive connects later, after keyboard and mouse come off. The display has no audio;
the USB speaker is ATOM's voice, and the installer selects it automatically.

The Pi receives power from the official 27W supply — mandatory, since the
Pi now feeds the display as well.

# `5. Before pressing the power button` 

Your desk should now look approximately like:

- CAMERA
- │
- │
- ┌──────┴──────┐
- │ Raspberry   │
- │   Pi 5      │
- │             │
- │ PCIe / M.2  │
- │    HAT      │
- └──────┬──────┘
- │
- NVMe + Hailo

- USB MIC ─────┤
- USB LIBRARY ─┤ optional
- │
- ▼
- TOUCHSCREEN
- Official Pi 27W PSU
- │
- ▼
- POWER
- Check:
- Pi is not powered yet
- cooler installed
- HAT secured
- NVMe secured
- Hailo secured
- camera cable connected
- USB microphone connected
- screen connected
- Pi's official power supply ready
- microSD prepared
- keyboard/mouse available
- network available
- 6. Prepare the microSD card

Use Raspberry Pi Imager on another computer.

Choose:

Raspberry Pi OS — 64-bit — Desktop

The ATOM-Pi README explicitly requires the Desktop version.

Before writing the card, configure:

- username
- password
- Wi-Fi
- timezone
- SSH

Then write the card.

Insert the microSD card into the Pi.

## 7. NOW press the power button

This is the first point at which you power the system.

Connect the official 27W USB-C supply.

Press the Pi power button.

Wait for Raspberry Pi OS to boot.

You should arrive at the normal Raspberry Pi desktop.

Do not expect ATOM yet.

At this point you're just establishing a working Pi.

## 8. First Pi setup

Connect:

- keyboard
- mouse
- network

Open Terminal.

Run:

```bash
sudo apt update
```

Then:

```bash
sudo apt full-upgrade -y
```

Reboot if Raspberry Pi OS asks you to.

Then open Terminal again.

## 9. Get ATOM-Pi

You can use the repository directly.

For the easiest installation, the project's installer is designed to be run
with:

```bash
curl -fsSL https://raw.githubusercontent.com/zlipson1999/ATOM-Pi/main/install.sh | bash
```

The installer explicitly says do not run it as root; run it as your normal Pi
user.

Important

The installer is resumable.

It records progress in:

~/.atom-pi-stage

and writes its installation log to:

~/atom-pi-install.log
## 10. What happens during installation
The installer has three major stages.

Stage 0

It updates the Pi and firmware.

Then:

REBOOT

When the Pi comes back:

```bash
curl -fsSL https://raw.githubusercontent.com/zlipson1999/ATOM-Pi/main/install.sh | bash
```

again.

Stage 1

It enables PCIe Gen 3 and checks:

Hailo detected
NVMe detected

The installer requires both.

If the Pi is still booting from microSD, it stops and gives you the one manual
migration step.

## 11. Move Raspberry Pi OS to NVMe

When the installer tells you you're still booting from microSD:

Open:

Raspberry Pi menu → Accessories → SD Card Copier

Then:

Copy From:
microSD / mmcblk0

Copy To:
NVMe / nvme0n1
Let it finish.

Then:

Terminal →

```bash
sudo raspi-config
```

Choose:

```
6 Advanced Options
    ↓
Boot Order
    ↓
NVMe/USB Boot
```

Then shut down.

Remove the microSD card.

Power the Pi back on.

Run the installer again.

This is the exact manual SSD migration procedure currently described by
install.sh.

# `12. Hailo installation` 

The next installer stage installs:

hailo-all

Then the Pi reboots again.

Run the installer again.

The next stage verifies:

```bash
hailortcli fw-control identify
```

The installer will not simply pretend Hailo works if the hardware isn't
responding.

# `13. Final ATOM installation` 

The installer then handles the large software portion:

- system packages
- Python environment
- pocket-ai
- Qwen3-4B
- Piper voice
- Ollama
- Moondream
- ATOM patches
- robot GUI
- knowledge library
- wake-word infrastructure
- autostart

The current installer configures Qwen3-4B Q4_K_M and the British Piper voice.

It also installs the optional Kiwix/document-library support.

# `14. Don't panic when Hey ATOM isn't ready` 

This is intentional.

The installer must not fabricate:

hey_atom.onnx

If you haven't trained your wake word yet, the touchscreen microphone still
works.

That's expected.

You eventually create:

hey_atom.onnx

using the pipeline in:

wakeword/

Then place it into the project and rerun the appropriate installation/update
process.

The README explicitly says the wake model is a trained neural model, not
something that can simply be generated by writing "Hey ATOM" into a
configuration file.

# `15. How to get Claude Code onto the Pi` 

Once Raspberry Pi OS is working and you have Terminal access, install Claude
Code using Anthropic's current official installation instructions rather than
hard-coding an old installer command into ATOM-Pi's build guide.

The important part is that Claude Code runs inside the terminal, from the ATOM-
Pi repository.

After Claude Code is installed and authenticated, you want:

```bash
cd ~/atom-pi
claude
```

Then Claude Code will see:

~/atom-pi/CLAUDE.md

and that file becomes its operating instructions.

Your repository's CLAUDE.md explicitly tells the agent to read it first, inspect
the repository, make minimal changes, test what can be tested, and never claim
physical hardware validation that it hasn't actually performed.

# `16. What to tell Claude Code` 

When Claude Code starts, don't give it another giant architecture prompt.

Start with:

Read CLAUDE.md first.

Then inspect the entire ATOM-Pi repository and determine the current
implementation status.

Do not redesign the architecture or add features.

Run the appropriate diagnostics and software tests that can be
performed in the current environment.

Identify anything that requires physical Raspberry Pi hardware
validation.

Do not claim hardware functionality from simulation or compilation.

If something is broken, fix the smallest verified problem and test
the fix.

At the end, report:

1. what you inspected,

2. what you changed,

3. what passed,

4. what could not be tested,

5. remaining blockers,

6. the exact next physical action I need to perform.

That's it.

Your CLAUDE.md is already doing most of the prompting.

## 17. First Claude Code command

Once Claude is installed:

```bash
cd ~/atom-pi
```

Then:

claude

Once inside Claude Code:

Read CLAUDE.md and begin the ATOM-Pi build/validation process.
Do not redesign anything. Start by inspecting the repository and
current installation state.

Let Claude inspect first.

Do not immediately tell it to rewrite things.

# `18. First ATOM launch` 

Once the installer reports completion, reboot:

```bash
sudo reboot
```

ATOM is designed to start automatically after installation. The README says the
first launch may finish model downloads before the system is ready.

You should eventually see the full ATOM robot, not merely a face:

          ┌─────────────┐
          │    ATOM     │

<!-- Start of picture text -->
          │   VISOR     │<br>          └──────┬──────┘<br>             shoulders<br>        ┌────────┼────────┐<br>       /         │         \<br>     ARM       TORSO       ARM<br>       \         │         /<br>        └────────┼────────┘<br>             ┌───●───┐<br>             │ CORE  │<br>             └───────┘<br><!-- End of picture text -->

The actual implementation has the robot state-driven by backend events. Thinking
raises the arm and taps the head; speaking animates the mouth/core.

# `19. First test` 

Don't start with the hardest test.

First verify:

Screen

ATOM appears.

Audio

Use:

```bash
# atom_doctor.py lives in ~/pocket-ai — start there, or the commands
# below will fail with "can't open file".
cd ~/pocket-ai && source .venv/bin/activate

# Speaker
python atom_doctor.py --sound
# Microphone
python atom_doctor.py --mic
# Overall diagnostics
python atom_doctor.py
```

Then manually:

Press the microphone button.

Say:

Hello ATOM.

Confirm that:

```
MIC
 ↓
WHISPER
 ↓
BRAIN
 ↓
PIPER
 ↓
SPEAKER
```

works.

## 20. Then test the robot

Ask a normal question.
You should see:

LISTENING

     ↓

```
THINKING
     ↓
ARM RAISES
     ↓
HAND TAPS HEAD
     ↓
ARM RETURNS
     ↓
SPEAKING
     ↓
IDLE
```

That's the ATOM behavior you designed.

## 21. Then test the eyes

Ask:

Hey ATOM, what do you see?

The intended pipeline is:

HEY ATOM

```
   ↓
EARS
   ↓
CAMERA
   ↓
HAILO / MOONDREAM
   ↓
BRAIN
   ↓
PIPER
   ↓
MOUTH
```

```
The README's acceptance contract specifically requires the complete ears → eyes
→ brain → mouth → body interaction rather than treating individual components as
sufficient.
```

## 22. Then connect your USB library

Create a folder on the external drive called:

atom-library

Put your .zim, PDF, EPUB, TXT, or Markdown content there.

Connect the drive.

ATOM's knowledge system is designed so that:

```
USB DRIVE
    │
    ├── Wikipedia ZIM
    ├── Kiwix content
    ├── PDFs
    ├── EPUBs
    └── TXT/MD
         │
         ↓
    LOCAL INDEX
         │
         ↓
```

       ATOM

The large source files remain on the USB drive.

## 23. And you still have a normal PC

This is important given what you told me earlier.

ATOM-Pi is not intended to trap you inside the robot interface.

The README explicitly describes a desktop mode where the ATOM services can be
suspended and the Pi's resources returned to normal desktop use for:

- browsing
- downloading
- files
- terminal
- managing the library

Then you can return to ATOM without reinstalling or rebooting.

## 24. The final test

Once everything above works, follow:

VALIDATION.md

Do not let Claude mark the physical tests complete.

You physically verify:

BOOT

```
 ↓
SELF CHECK
 ↓
IDLE
 ↓
"HEY ATOM"
```

```
 ↓
LISTENING
 ↓
USER QUESTION
 ↓
SEEING if required
 ↓
THINKING
 ↓
ARM RAISES
```

 ↓
HAND TAPS HEAD

 ↓
ARM RETURNS

 ↓
SPEAKING

 ↓
MOUTH / CORE REACT

 ↓
IDLE

Then test:

- wake reliability
- self-triggering
- barge-in

- camera
- Hailo
- internet
- USB library
- library disconnect/reconnect
- desktop mode
- sustained thermal operation

That is the actual finish line.

One change I strongly recommend to the repo

I would add exactly this document as:

BUILD.md

and then add this one line near the top of README.md:

## Building ATOM-Pi

For the complete first-time, solder-free assembly and software setup,
see [BUILD.md](BUILD.md).

That gives you a very clean three-document system:

- README.md
- │
- └── What is ATOM-Pi?

- BUILD.md
- │
- └── How do I physically build and install it?

- VALIDATION.md
- │
- └── How do I prove it actually works?

And CLAUDE.md remains separate:

- CLAUDE.md
- │
- └── How Claude Code is allowed to work on it

---
# 25. FINAL ATOM-Pi OPERATING CONTRACT
This section defines the final intended ATOM-Pi experience and the handoff from the human builder to the AI coding agent.
The existing build instructions above remain authoritative for the physical construction and installation procedure. This section adds the final integration, UX, agent, storage, validation, and completion requirements.
## 25.1 Claude Code is the primary build agent
Once Raspberry Pi OS is operational and the ATOM-Pi repository is available, Claude Code is the primary software-building and troubleshooting agent.
The repository must contain:
```text
CLAUDE.md
Claude Code must read CLAUDE.md before modifying the project.
Start Claude from the ATOM-Pi repository:
cd ~/atom-pi
claude
Initial instruction:
Read CLAUDE.md first.
Inspect the complete ATOM-Pi repository and determine the current
implementation and installation state.
Do not redesign the architecture.
Do not add speculative features.
Run every software-side diagnostic and test that can be performed
on this machine.
Identify anything that requires physical Raspberry Pi validation.
Do not claim physical hardware functionality from simulation,
documentation, compilation, or static inspection.
If you find a real defect, make the smallest verified fix and test it.
At the end report:
1. What you inspected
2. What you changed
3. What passed
4. What could not be tested
5. Remaining blockers
6. The exact next human action
Claude must follow the repository's CLAUDE.md rules rather than inventing a new architecture.
### 25.2 Source-of-truth hierarchy
When two pieces of information disagree, use this order:
1. Actual tested ATOM-Pi code
2. Pinned upstream implementation
3. Repository documentation
4. README/build-guide assumptions
Do not endlessly reconcile contradictory documentation when executable behavior establishes the truth.
Do not unpin upstream commits simply because a newer upstream version exists.
Do not redesign a working subsystem without a demonstrated defect.
### 25.3 No speculative feature creep
The objective is to complete and harden the defined ATOM-Pi experience.
Do not add capabilities merely because they are technically interesting.
Prioritize:
IMPLEMENT
INTEGRATE
TEST
HARDEN
VALIDATE
before adding optional functionality.
Prefer the simplest architecture that reliably delivers the complete ATOM-Pi experience.
Every additional dependency, model, service, abstraction, or subsystem must justify its complexity.
## 26. The ATOM experience
ATOM-Pi is not intended to be merely a face on a screen.
The visible robot should be a consistent full-body robot companion inspired by the physical proportions and presence of a boxing/sparring robot.
The screen should show the complete robot:
              HEAD
          ┌───────────┐
          │   EYES    │
          │   MOUTH   │
          └─────┬─────┘
                │
          ┌─────┴─────┐
          │ SHOULDERS │
       ARM│   TORSO   │ARM
          │     ●     │
          │   CORE    │
          └───────────┘
The chest contains a prominent circular power-core element.
The robot's visual identity must remain consistent across:
idle
listening
seeing
thinking
speaking
tool use
web use
knowledge-library search
errors
boot
desktop transition
Do not redesign the robot for individual screens.
The robot should always look like the same ATOM.
## 27. Thinking gesture
When ATOM is genuinely processing a response, the robot must visibly communicate that state.
The intended gesture is:
THINKING_STARTED
      ↓
ARM RAISES
      ↓
HAND TAPS HEAD
      ↓
THINKING CONTINUES
      ↓
RESPONSE READY
      ↓
ARM RETURNS
The animation must be driven by actual backend state.
It must not merely play a decorative animation whenever text appears.
The architecture should allow the same state event to eventually drive physical actuators without rewriting the assistant state system.
For example:
THINKING_STARTED
       ↓
ROBOT GESTURE EVENT
       ├── Screen animation
       └── Future physical actuator
Physical motors/servos are not required for the current build.
## 28. Full-body identity
ATOM must maintain persistent visual identity.
The following should remain consistent:
head proportions
eyes
mouth
chest core
torso
arms
overall proportions
colors/material language
gesture vocabulary
Do not replace the robot with a generic chatbot avatar.
Do not use BMO artwork or another character's artwork as the ATOM identity.
The implementation should remain original while capturing the intended robot presence.
## 29. No dead eyes
ATOM must not look frozen or dead while waiting for a response.
During longer operations use subtle activity such as:
eye movement
eye state changes
chest-core activity
breathing/body motion
listening indication
thinking indication
speaking indication
Do not create excessive animation merely for decoration.
The goal is to communicate that the system is alive and working.
30. Voice-first / hands-free operation
Normal ATOM operation is voice-first.
The user should not need to touch the screen for ordinary interaction.
The intended interaction is:
"Hey ATOM"
      ↓
LISTENING
      ↓
USER SPEAKS
      ↓
ATOM RESPONDS
Touch remains available as a secondary control surface.
The microphone button must remain available when wake-word operation has not yet been physically validated.
31. Ambient-awareness boundary
ATOM must have a clear privacy boundary.
Wake-word detection may remain locally active.
Full speech capture and contextual camera processing should begin only when required by the interaction.
The user should be able to understand when ATOM is:
IDLE
LISTENING
SEEING
THINKING
SPEAKING
The system must not falsely imply that the camera or microphone is inactive when it is actually active.
32. Internet access
ATOM-Pi is:
LOCAL-FIRST
+
INTERNET-CAPABLE
It is not an offline-only system.
Local models and local resources should be preferred where appropriate.
Internet tools may be used when the task requires current or external information and network access is available.
The system must clearly distinguish local resources from internet resources.
The personality layer must never claim that a web lookup occurred if it did not.
Likewise, it must never claim that information came from a local library if the library was not actually queried.
33. Desktop access
ATOM-Pi must not permanently trap the Raspberry Pi inside a kiosk interface.
The user must retain normal Raspberry Pi desktop access when needed.
Desktop access may be used for:
downloading files
browsing
managing storage
managing the USB library
opening terminals
configuring the system
ordinary computer use
Desktop mode should suspend or reduce ATOM's resource-intensive AI/camera processes as appropriate so normal desktop operation remains usable.
The desktop is an escape hatch and normal computer environment, not a separate ATOM product.
34. MicroSD and NVMe storage
The preferred primary system storage is NVMe.
After the system has been successfully migrated to NVMe and NVMe boot has been verified, the microSD card may remain inserted as secondary/removable storage.
The microSD may be used for:
downloads
ordinary files
temporary storage
backups
other non-critical data
Do not treat the microSD as the primary ATOM-Pi system disk once NVMe boot has been established.
Keep critical software, models, and the operating system on NVMe.
35. External USB knowledge library
The large external USB drive is OPTIONAL.
ATOM-Pi must function without it.
If connected, the drive may contain:
Kiwix .zim files
PDFs
EPUBs
TXT
Markdown
other supported reference material
The source documents should remain on the external drive.
Do NOT copy an entire multi-terabyte library onto the Raspberry Pi.
The intended architecture is:
USB LIBRARY DRIVE
       ↓
LOCAL SEARCH / INDEX
       ↓
ATOM KNOWLEDGE MODULE
       ↓
ATOM
The local index may be stored on the Pi, while the large source content remains on the USB drive.
The system must tolerate the drive being disconnected.
If the drive is absent:
LIBRARY = DEGRADED / UNAVAILABLE
not:
SYSTEM FAILURE
The optional library must never prevent ATOM from operating normally.
36. Kiwix library
Kiwix .zim content may be accessed from the external USB drive.
The system should use the actual Kiwix retrieval mechanism rather than pretending the content has been indexed when it has not.
The exact mechanism must follow the implementation in the repository.
Do not invent search results.
Do not claim that ATOM consulted a Kiwix source unless the source was actually queried.
37. Source provenance
For development and debugging, ATOM should be able to identify the source/capability that handled a request.
Examples:
LOCAL
QWEN
VISION
HAILO
PIPER
WEB
USB LIBRARY
KIWIX
This is provenance, not chain-of-thought.
Do not expose private reasoning or chain-of-thought.
A developer should be able to determine:
Which subsystem handled this?
without being shown hidden reasoning.
38. System-event trace
For development/debugging, expose system events rather than chain-of-thought.
Example:
Wake detected
      ↓
Transcript received
      ↓
Intent identified
      ↓
Vision requested
      ↓
Fresh frame captured
      ↓
Vision result received
      ↓
Model selected
      ↓
Tool invoked
      ↓
Response generated
      ↓
TTS started
      ↓
Speaking
Do not expose private reasoning.
The trace is for debugging the multimodal pipeline.
39. Graceful hardware failures
If a hardware capability is unavailable, ATOM must respond naturally.
Bad:
AttributeError: camera_frame is None
Good:
I can't access the camera right now.
Likewise:
I can't hear you right now.
or:
The library drive isn't available right now.
The personality layer must not conceal the actual failure.
40. Personality cannot override system truth
ATOM may be friendly, humorous, conversational, or expressive.
However:
Personality must never override system truth.
ATOM must never pretend:
that it saw something it did not see
that it heard something it did not hear
that a web search occurred when it did not
that a library source was consulted when it was not
that a model is operational when it is not
that hardware passed validation when it did not
The robot can be charming.
It cannot fake capability.
41. Vision freshness
For questions about the current environment, ATOM should use a newly captured camera frame unless the system can prove that an existing frame is sufficiently current.
Avoid stale-frame answers.
For example:
"What is on my desk right now?"
must not be answered using an old camera frame simply because one happens to be cached.
42. Vision uncertainty
ATOM must distinguish between confidence and uncertainty.
If the vision system is uncertain, it should communicate that naturally.
For example:
I think that's a...
rather than confidently inventing an object.
The personality must not turn uncertain vision output into false certainty.
43. DEMO / SIMULATION versus LIVE HARDWARE
The project must distinguish:
DEMO / SIMULATION
from:
LIVE HARDWARE
A simulator can demonstrate:
UI
state transitions
animations
robot gestures
event routing
but it cannot prove:
microphone reliability
speaker behavior
camera operation
wake-word accuracy
Hailo hardware operation
thermal stability
physical barge-in behavior
Simulation is not hardware validation.
44. Hardware safety
Because ATOM-Pi is intended for a physical enclosure, use safe construction practices.
Do not leave:
exposed dangerous electrical connections
unsecured wiring
unsupported boards
improperly mounted power supplies
Provide:
cable strain relief
ventilation
thermal clearance
secure board mounting
appropriate power supplies
If physical arm/hand movement is added later:
use safe servo/motor voltage
provide mechanical limits
avoid pinch points
avoid uncontrolled movement
provide a safe shutdown state
The screen animation must remain safe even if future physical actuation is introduced.
45. Versioned architecture
Every validated ATOM-Pi build should be identifiable by:
ATOM-Pi version
Architecture version
Model versions
Hardware revision
Upstream commit SHAs
The purpose is reproducibility.
A future user should be able to determine exactly which combination produced a working build.
Do not silently update pinned components.
46. Startup/status screen
ATOM should provide a human-readable startup status.
Example:
ATOM-Pi
────────────────────────
✓ Audio
✓ Wake Word
✓ Camera
✓ Hailo
✓ Brain
✓ Voice
✓ Face
✓ Internet
✓ Knowledge Library
READY
The actual status must reflect reality.
If something is unavailable:
⚠ Camera
or:
DEGRADED — USB Library unavailable
Do not show a green check merely because configuration files exist.
47. Diagnostics
The project must provide clear diagnostics.
Use:
python atom_doctor.py
and the supported diagnostic flags:
python atom_doctor.py --logs
python atom_doctor.py --version
python atom_doctor.py --sound
python atom_doctor.py --mic
The installation log should be consulted before guessing:
~/atom-pi-install.log
Diagnostics should distinguish:
PRESENT
FUNCTIONAL
PHYSICALLY VALIDATED
These are not interchangeable.
48. Wake-word model honesty
The file:
hey_atom.onnx
must NEVER be fabricated.
Never create:
an empty file
a dummy model
a renamed unrelated model
a placeholder model
a fake ONNX file
a model merely intended to satisfy a readiness check
If the actual model has not been produced:
Wake Word = OFF
The microphone interaction remains available.
The wake-word pipeline is documented under:
wakeword/
The model is not considered validated merely because the file exists.
Physical microphone testing remains mandatory.
49. Hardware gate
Hardware-dependent acceptance criteria belong to physical testing.
The coding agent must prepare everything that can be prepared from the terminal.
The human must perform tests requiring:
physically speaking
physically listening
observing the physical display
camera operation
real wake-word behavior
real speaker/microphone behavior
real thermals
physical cables
physical USB drive behavior
Never mark these tests PASS from code compilation or simulation.
50. Completion states
Use exactly these concepts:
READY FOR HARDWARE TESTING
Software is prepared and tested as far as possible, but physical validation remains.
READY
Required physical acceptance tests have actually passed.
NOT READY — REQUIRES FIXES
A software defect, unresolved dependency, or implementation blocker remains.
The presence of a file is not equivalent to functional readiness.
51. ATOM-Pi GOLDEN PATH
Create and maintain one acceptance scenario called:
ATOM-Pi GOLDEN PATH
The intended sequence is:
BOOT
  ↓
SELF-CHECK
  ↓
IDLE ROBOT
  ↓
"HEY ATOM"
  ↓
LISTENING
  ↓
USER QUESTION
  ↓
SEEING if needed
  ↓
THINKING
  ↓
ARM RAISES
  ↓
HAND TAPS HEAD
  ↓
REASONING FINISHES
  ↓
ARM RETURNS
  ↓
SPEAKING
  ↓
CHEST CORE / FACE REACT
  ↓
IDLE
The critical end-to-end test is:
"Hey ATOM, what do you see?"
This must prove:
EARS
 ↓
EYES
 ↓
BRAIN
 ↓
MOUTH
 ↓
BODY
on real hardware.
52. Final validation matrix
The final ATOM-Pi validation should cover:
[ ] Pi boots
[ ] NVMe boots
[ ] Hailo detected and functional
[ ] Camera works
[ ] Microphone works
[ ] Speaker works
[ ] Voice interaction works
[ ] Wake word physically validated
[ ] Vision works
[ ] Local brain works
[ ] Robot GUI works
[ ] Full-body robot visible
[ ] Thinking gesture works
[ ] Speaking animation works
[ ] Internet tools work
[ ] Internet failure is handled gracefully
[ ] USB library works when attached
[ ] USB library absence is non-fatal
[ ] Kiwix retrieval works
[ ] Desktop access works
[ ] Barge-in works
[ ] Sustained thermal test passes
[ ] Golden Path passes
Any hardware item that has not physically been tested remains unresolved.
53. Do not overengineer
The final objective is not to create an endlessly expanding robotics experiment.
The objective is:
Build the defined ATOM-Pi experience reliably.
Prefer:
SIMPLE
REPRODUCIBLE
TESTABLE
LOCAL-FIRST
HONEST
over unnecessary abstraction.
Once the defined requirements are satisfied, do not redesign the architecture merely because a different approach is theoretically cleaner.
54. Final human → Claude → hardware workflow
The complete workflow is:
PHYSICAL BUILD
      ↓
POWER ON
      ↓
RASPBERRY PI OS
      ↓
NETWORK
      ↓
ATOM-Pi REPOSITORY
      ↓
CLAUDE CODE
      ↓
CLAUDE READS CLAUDE.md
      ↓
INSTALL / DIAGNOSE / TEST
      ↓
SOFTWARE READY
      ↓
HUMAN HARDWARE VALIDATION
      ↓
GOLDEN PATH
      ↓
ATOM-Pi READY
The human should not need to become a Linux expert to operate this workflow.
Claude should explain actions in plain language and clearly identify when human physical intervention is required.
55. Final rule
Do not confuse:
CODE EXISTS
with:
SYSTEM WORKS
Do not confuse:
MODEL FILE EXISTS
with:
MODEL IS VALIDATED
Do not confuse:
SIMULATION PASSED
with:
HARDWARE PASSED
Do not confuse:
INSTALL COMPLETE
with:
ATOM-Pi READY
The final authority is evidence from the actual system and the physical acceptance tests.
ATOM-Pi should be declared READY only when the defined Golden Path and required hardware validation have actually passed.


