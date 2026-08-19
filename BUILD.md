```
ATOM-Pi — Solder-Free Build Guide
1. What you are building
```

```
ATOM-Pi is a Raspberry Pi 5 robot companion with:
```

```
full-body animated robot interface
voice input/output
"Hey ATOM" wake word
camera vision
Hailo acceleration
local Qwen brain
local Moondream vision
optional USB knowledge library
internet access when needed
normal Raspberry Pi desktop access
physical hardware validation after software installation
```

```
The robot's on-screen body is the robot. It is not just a face: head, eyes,
mouth, neck, shoulders, torso, two arms/hands, and chest power core are rendered
together. During thinking, the arm raises and taps the robot's head.
```

```
2. Parts
Required
PartWhat it does
Raspberry Pi 5 16GBMain computer
Official 27W USB-C Pi supplyPower
Active coolerKeeps Pi cool under sustained AI load
32GB+ A2 microSDInitial boot
USB microphoneEars
Keyboard + mouseInitial setup
Wi-Fi/EthernetInternet during setup
```

```
The README says 8GB can work, but 16GB is the comfortable configuration.
```

```
Recommended for the complete build
NVMe M.2 2280 500GB
Dual M.2 PCIe-switch HAT / ASM2806
Hailo-8L M.2 module, B+M key
Raspberry Pi Camera Module 3
correct Pi 5 22-pin camera cable
SunFounder 10" touchscreen
USB knowledge-library drive
Do NOT buy
```

```
Raspberry Pi AI HAT+
```

```
The README specifically calls this out because it conflicts with the SSD/Hailo
configuration being used by ATOM-Pi.
```

```
3. No soldering
```

```
You do not need to solder anything for the ATOM-Pi configuration.
```

```
The physical build is:
```

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

```
     └── Display connection → touchscreen
```

```
Use the mechanical instructions supplied with the specific HAT and modules for
inserting/securing the M.2 cards. Do not force an M.2 module into a slot.
```

```
4. Assemble the Pi while it is OFF
```

```
Do not connect power yet.
```

```
Step 1 — Pi
```

```
Put the Raspberry Pi 5 on a clean, non-conductive surface.
```

```
Do not power it.
```

```
Step 2 — Cooling
```

```
Install the active cooler according to the cooler manufacturer's instructions.
```

```
The cooler is required because ATOM-Pi runs sustained local AI workloads.
```

```
Step 3 — PCIe/M.2 board
```

```
Attach the dual M.2 PCIe-switch HAT to the Pi according to the HAT's supplied
mechanical instructions.
```

```
Do not improvise a cable orientation.
```

```
Step 4 — NVMe
```

```
Install the NVMe M.2 2280 SSD into the appropriate M.2 slot.
```

```
Secure it with the supplied retaining hardware.
```

```
Step 5 — Hailo
```

```
Install the Hailo-8L M.2 B+M-key module into its designated M.2 slot.
```

```
Secure it.
```

```
The ATOM-Pi installer specifically expects both Hailo and NVMe to appear on
PCIe.
```

```
Step 6 — Camera
```

```
Connect the Camera Module 3 using the Pi 5 22-pin cable.
```

```
The README specifically warns that the camera ships with the wrong cable for
this setup.
```

```
Step 7 — Microphone
```

```
Plug the USB microphone into USB.
```

```
Step 8 — Optional library
```

```
If you are using your large USB library drive, connect it to USB.
```

```
Do not copy your entire Kiwix library onto the Pi.
```

```
ATOM-Pi's library design keeps the content on the external drive and keeps only
a compact search index locally.
```

```
Step 9 — Screen
```

```
Connect the touchscreen according to its supplied instructions.
```

```
The Pi itself should receive power from the official 27W Pi power supply.
```

```
Do not power the Pi from the screen's USB-C output. The README explicitly warns
against that configuration.
```

# `5. Before pressing the power button` 

```
Your desk should now look approximately like:
```

```
                 CAMERA
                    │
                    │
             ┌──────┴──────┐
             │ Raspberry   │
             │   Pi 5      │
             │             │
             │ PCIe / M.2  │
             │    HAT      │
             └──────┬──────┘
                    │
              NVMe + Hailo
```

```
       USB MIC ─────┤
       USB LIBRARY ─┤ optional
              │
              ▼
          TOUCHSCREEN
       Official Pi 27W PSU
              │
              ▼
           POWER
Check:
 Pi is not powered yet
 cooler installed
 HAT secured
 NVMe secured
 Hailo secured
 camera cable connected
 USB microphone connected
 screen connected
 Pi's official power supply ready
 microSD prepared
 keyboard/mouse available
 network available
6. Prepare the microSD card
```

```
Use Raspberry Pi Imager on another computer.
```

```
Choose:
```

```
Raspberry Pi OS — 64-bit — Desktop
```

```
The ATOM-Pi README explicitly requires the Desktop version.
```

```
Before writing the card, configure:
```

```
username
password
Wi-Fi
timezone
SSH
```

```
Then write the card.
```

```
Insert the microSD card into the Pi.
```

`7. NOW press the power button` 

```
This is the first point at which you power the system.
```

```
Connect the official 27W USB-C supply.
```

```
Press the Pi power button.
```

```
Wait for Raspberry Pi OS to boot.
```

```
You should arrive at the normal Raspberry Pi desktop.
```

```
Do not expect ATOM yet.
```

```
At this point you're just establishing a working Pi.
```

`8. First Pi setup` 

```
Connect:
```

```
keyboard
mouse
network
```

```
Open Terminal.
```

```
Run:
```

```
sudo apt update
```

```
Then:
```

```
sudo apt full-upgrade -y
```

```
Reboot if Raspberry Pi OS asks you to.
```

```
Then open Terminal again.
```

`9. Get ATOM-Pi` 

```
You can use the repository directly.
```

```
For the easiest installation, the project's installer is designed to be run
with:
```

```
curl -fsSL https://raw.githubusercontent.com/zlipson1999/atom-pi/main/install.sh
| bash
```

```
The installer explicitly says do not run it as root; run it as your normal Pi
user.
```

```
Important
```

```
The installer is resumable.
```

```
It records progress in:
```

```
~/.atom-pi-stage
```

```
and writes its installation log to:
```

```
~/atom-pi-install.log
10. What happens during installation
```

```
The installer has three major stages.
```

```
Stage 0
```

```
It updates the Pi and firmware.
```

```
Then:
```

```
REBOOT
```

```
When the Pi comes back:
```

```
curl -fsSL https://raw.githubusercontent.com/zlipson1999/atom-pi/main/install.sh
| bash
```

```
again.
```

```
Stage 1
```

```
It enables PCIe Gen 3 and checks:
```

```
Hailo detected
NVMe detected
```

```
The installer requires both.
```

```
If the Pi is still booting from microSD, it stops and gives you the one manual
migration step.
```

```
11. Move Raspberry Pi OS to NVMe
```

```
When the installer tells you you're still booting from microSD:
```

```
Open:
```

```
Raspberry Pi menu → Accessories → SD Card Copier
```

```
Then:
```

```
Copy From:
microSD / mmcblk0
```

```
Copy To:
NVMe / nvme0n1
Let it finish.
```

```
Then:
```

```
Terminal →
```

```
sudo raspi-config
```

```
Choose:
```

```
6 Advanced Options
    ↓
Boot Order
    ↓
NVMe/USB Boot
```

```
Then shut down.
```

```
Remove the microSD card.
```

```
Power the Pi back on.
```

```
Run the installer again.
```

```
This is the exact manual SSD migration procedure currently described by
install.sh.
```

# `12. Hailo installation` 

```
The next installer stage installs:
```

```
hailo-all
```

```
Then the Pi reboots again.
```

```
Run the installer again.
```

```
The next stage verifies:
```

```
hailortcli fw-control identify
```

```
The installer will not simply pretend Hailo works if the hardware isn't
responding.
```

# `13. Final ATOM installation` 

```
The installer then handles the large software portion:
```

```
system packages
Python environment
pocket-ai
Qwen3-4B
Piper voice
Ollama
Moondream
ATOM patches
robot GUI
knowledge library
wake-word infrastructure
autostart
```

```
The current installer configures Qwen3-4B Q4_K_M and the British Piper voice.
```

```
It also installs the optional Kiwix/document-library support.
```

# `14. Don't panic when Hey ATOM isn't ready` 

```
This is intentional.
```

```
The installer must not fabricate:
```

```
hey_atom.onnx
```

```
If you haven't trained your wake word yet, the touchscreen microphone still
works.
```

```
That's expected.
```

```
You eventually create:
```

```
hey_atom.onnx
```

```
using the pipeline in:
```

```
wakeword/
```

```
Then place it into the project and rerun the appropriate installation/update
process.
```

```
The README explicitly says the wake model is a trained neural model, not
something that can simply be generated by writing "Hey ATOM" into a
configuration file.
```

# `15. How to get Claude Code onto the Pi` 

```
Once Raspberry Pi OS is working and you have Terminal access, install Claude
Code using Anthropic's current official installation instructions rather than
hard-coding an old installer command into ATOM-Pi's build guide.
```

```
The important part is that Claude Code runs inside the terminal, from the ATOM-
Pi repository.
```

```
After Claude Code is installed and authenticated, you want:
```

```
cd ~/atom-pi
claude
```

```
Then Claude Code will see:
```

```
~/atom-pi/CLAUDE.md
```

```
and that file becomes its operating instructions.
```

```
Your repository's CLAUDE.md explicitly tells the agent to read it first, inspect
the repository, make minimal changes, test what can be tested, and never claim
physical hardware validation that it hasn't actually performed.
```

# `16. What to tell Claude Code` 

```
When Claude Code starts, don't give it another giant architecture prompt.
```

```
Start with:
```

```
Read CLAUDE.md first.
```

```
Then inspect the entire ATOM-Pi repository and determine the current
implementation status.
```

```
Do not redesign the architecture or add features.
```

```
Run the appropriate diagnostics and software tests that can be
performed in the current environment.
```

```
Identify anything that requires physical Raspberry Pi hardware
validation.
```

```
Do not claim hardware functionality from simulation or compilation.
```

```
If something is broken, fix the smallest verified problem and test
the fix.
```

```
At the end, report:
```

`1. what you inspected,` 

`2. what you changed,` 

`3. what passed,` 

`4. what could not be tested,` 

`5. remaining blockers,` 

`6. the exact next physical action I need to perform.` 

```
That's it.
```

```
Your CLAUDE.md is already doing most of the prompting.
```

`17. First Claude Code command` 

```
Once Claude is installed:
```

```
cd ~/atom-pi
```

```
Then:
```

```
claude
```

```
Once inside Claude Code:
```

```
Read CLAUDE.md and begin the ATOM-Pi build/validation process.
Do not redesign anything. Start by inspecting the repository and
current installation state.
```

```
Let Claude inspect first.
```

```
Do not immediately tell it to rewrite things.
```

# `18. First ATOM launch` 

```
Once the installer reports completion, reboot:
```

```
sudo reboot
```

```
ATOM is designed to start automatically after installation. The README says the
first launch may finish model downloads before the system is ready.
```

```
You should eventually see the full ATOM robot, not merely a face:
```

```
          ┌─────────────┐
          │    ATOM     │
```



<!-- Start of picture text -->
          │   VISOR     │<br>          └──────┬──────┘<br>             shoulders<br>        ┌────────┼────────┐<br>       /         │         \<br>     ARM       TORSO       ARM<br>       \         │         /<br>        └────────┼────────┘<br>             ┌───●───┐<br>             │ CORE  │<br>             └───────┘<br><!-- End of picture text -->

```
The actual implementation has the robot state-driven by backend events. Thinking
raises the arm and taps the head; speaking animates the mouth/core.
```

# `19. First test` 

```
Don't start with the hardest test.
```

```
First verify:
```

```
Screen
```

```
ATOM appears.
```

```
Audio
```

```
Use:
```

```
python atom_doctor.py --sound
Microphone
python atom_doctor.py --mic
Overall diagnostics
python atom_doctor.py
Then manually:
```

```
Press the microphone button.
```

```
Say:
```

```
Hello ATOM.
```

```
Confirm that:
```

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

```
works.
```

```
20. Then test the robot
Ask a normal question.
You should see:
```

```
LISTENING
```

```
     ↓
```

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

```
That's the ATOM behavior you designed.
```

```
21. Then test the eyes
```

```
Ask:
```

```
Hey ATOM, what do you see?
```

```
The intended pipeline is:
```

```
HEY ATOM
```

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

```
22. Then connect your USB library
```

```
Create a folder on the external drive called:
```

```
atom-library
```

```
Put your .zim, PDF, EPUB, TXT, or Markdown content there.
```

```
Connect the drive.
```

```
ATOM's knowledge system is designed so that:
```

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

```
       ATOM
```

```
The large source files remain on the USB drive.
```

```
23. And you still have a normal PC
```

```
This is important given what you told me earlier.
```

```
ATOM-Pi is not intended to trap you inside the robot interface.
```

```
The README explicitly describes a desktop mode where the ATOM services can be
suspended and the Pi's resources returned to normal desktop use for:
```

```
browsing
downloading
files
terminal
managing the library
```

```
Then you can return to ATOM without reinstalling or rebooting.
```

```
24. The final test
```

```
Once everything above works, follow:
```

```
VALIDATION.md
```

```
Do not let Claude mark the physical tests complete.
```

```
You physically verify:
```

```
BOOT
```

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

```
 ↓
HAND TAPS HEAD
```

```
 ↓
ARM RETURNS
```

```
 ↓
SPEAKING
```

```
 ↓
MOUTH / CORE REACT
```

```
 ↓
IDLE
```

```
Then test:
```

```
wake reliability
self-triggering
barge-in
```

```
camera
Hailo
internet
USB library
library disconnect/reconnect
desktop mode
sustained thermal operation
```

```
That is the actual finish line.
```

```
One change I strongly recommend to the repo
```

```
I would add exactly this document as:
```

```
BUILD.md
```

```
and then add this one line near the top of README.md:
```

```
## Building ATOM-Pi
```

```
For the complete first-time, solder-free assembly and software setup,
see [BUILD.md](BUILD.md).
```

```
That gives you a very clean three-document system:
```

```
README.md
    │
    └── What is ATOM-Pi?
```

```
BUILD.md
    │
    └── How do I physically build and install it?
```

```
VALIDATION.md
    │
    └── How do I prove it actually works?
```

```
And CLAUDE.md remains separate:
```

```
CLAUDE.md
    │
    └── How Claude Code is allowed to work on it
```

