#!/usr/bin/env bash
# =============================================================================
#  atom-pi installer — one command, run it again after each reboot
#
#  Fresh Raspberry Pi 5 (OS already flashed) -> fully merged local AI:
#  pocket-ai chassis + wake word, face, Moondream vision, British voice.
#
#  Usage (either works):
#    curl -fsSL https://raw.githubusercontent.com/zlipson1999/ATOM-Pi/main/install.sh | bash
#  or, from inside a cloned/downloaded copy of this repo:
#    bash install.sh
#
#  The installer keeps progress in ~/.atom-pi-stage. When it needs a
#  reboot, it says so and reboots; run the SAME command again and it
#  continues where it left off. Expect THREE automatic reboots on a
#  stock image (system update, PCIe Gen 3 enable, Hailo driver), plus
#  one manual restart if you still need to migrate from microSD to the
#  NVMe drive. Run the same command after each one.
#
#  Once the install has completed, running it again performs a fast
#  SYNC instead: it re-copies the ATOM modules, picks up a newly
#  trained hey_atom.onnx, and re-applies the patches — no apt, no
#  model downloads, no npm. That is the supported way to add the wake
#  word after the fact. Force it explicitly with:  bash install.sh --sync
# =============================================================================
set -u

REPO_URL="${ATOM_REPO:-https://github.com/zlipson1999/ATOM-Pi.git}"
# Known-good upstream commits (the exact code all patches were verified
# against). Override with env vars to track newer upstream.
POCKET_SHA="${POCKET_SHA:-137fc627bd8c3e703db612332874023da7e3bb24}"
BMA_SHA="${BMA_SHA:-5fb755809583c8338b1205075b2d465baa9b49ef}"
STAGE_FILE="$HOME/.atom-pi-stage"
REPO_DIR="$HOME/atom-pi"
APP_DIR="$HOME/pocket-ai"
LOG="$HOME/atom-pi-install.log"

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '\033[32m  [ok]\033[0m %s\n' "$*"; }
warn()  { printf '\033[33m  [!!]\033[0m %s\n' "$*"; }
fail()  { printf '\033[31m  [FAILED]\033[0m %s\n' "$*"; }
stage() { echo "$1" > "$STAGE_FILE"; }
get_stage() { cat "$STAGE_FILE" 2>/dev/null || echo 0; }

die() {
  fail "$1"
  echo
  echo "  Fix the issue above, then run the installer again —"
  echo "  it will resume from this same stage."
  exit 1
}

reboot_and_continue() {
  echo
  bold ">>> A reboot is required. Rebooting in 10 seconds..."
  bold ">>> AFTER the Pi restarts, open a terminal and run the SAME"
  bold ">>> install command again. It will continue automatically."
  sleep 10
  sudo reboot
  exit 0
}

if [ "$(id -u)" -eq 0 ]; then
  die "Don't run this as root/sudo. Run it as your normal user; it uses sudo internally where needed."
fi

# -----------------------------------------------------------------------------
# Shared helpers used by BOTH the first install (stage 3) and the post-install
# sync path. Keeping them in one place is what makes "drop in hey_atom.onnx and
# run it again" work without re-doing apt, the model downloads, or npm.
# -----------------------------------------------------------------------------

# Locate this repo: the directory the script was run from if it looks like the
# repo, an existing clone, otherwise clone it fresh.
resolve_repo_dir() {
  _here="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)"
  if [ -n "$_here" ] && { [ -f "$_here/apply_patches.py" ] || [ -d "$_here/merged" ]; }; then
    REPO_DIR="$_here"
  elif [ ! -f "$REPO_DIR/apply_patches.py" ] && [ ! -d "$REPO_DIR/merged" ] \
       && [ ! -f "$REPO_DIR/patches/apply_patches.py" ]; then
    git clone "$REPO_URL" "$REPO_DIR" || die "could not clone $REPO_URL — check the URL at the top of install.sh"
  fi
}

# Copy the ATOM-owned modules, GUI components, and wake model into the
# pocket-ai tree, then apply the patches. Idempotent: safe to run repeatedly.
install_atom_layer() {
  # Canonical merged/ layout, or the files at the repository root (as the
  # current GitHub upload carries them).
  src() { if [ -f "$REPO_DIR/merged/$1" ]; then echo "$REPO_DIR/merged/$1"; else echo "$REPO_DIR/$1"; fi; }

  bold "Applying the ATOM merge (verified patches)"
  for f in wakeword_listener.py vision_describe.py atom_doctor.py atom_knowledge.py personality.txt; do
    cp "$(src "$f")" "$APP_DIR/" || die "ATOM module missing from the repo: $f"
  done
  # The wake-word banner below tells the user to run this ON the Pi, so it has
  # to actually be there. Non-fatal: it is a training tool, not a runtime one.
  REC="$REPO_DIR/wakeword/record_dataset.py"; [ -f "$REC" ] || REC="$REPO_DIR/record_dataset.py"
  if [ -f "$REC" ]; then cp "$REC" "$APP_DIR/record_dataset.py"
  else warn "record_dataset.py not found — dataset recorder won't be on the Pi"; fi
  # validate_model.py is installed under a clearer name next to the app.
  # Both locations are checked because the repo has carried it in each.
  VAL="$REPO_DIR/wakeword/validate_model.py"; [ -f "$VAL" ] || VAL="$REPO_DIR/validate_model.py"
  if [ -f "$VAL" ]; then
    cp "$VAL" "$APP_DIR/wakeword_validate.py"
  else
    warn "validate_model.py not found — live wake testing tool won't be on the Pi"
  fi
  for f in AtomRobot.jsx AtomRobotAdapter.jsx; do
    cp "$(src "$f")" "$APP_DIR/chat-gui/src/renderer/src/components/" \
      || die "robot component missing from the repo: $f"
  done
  PATCHER="$REPO_DIR/patches/apply_patches.py"; [ -f "$PATCHER" ] || PATCHER="$REPO_DIR/apply_patches.py"
  ( [ -f "$APP_DIR/.venv/bin/activate" ] && . "$APP_DIR/.venv/bin/activate"
    python3 "$PATCHER" "$APP_DIR" ) || warn "some patches printed manual follow-ups above — see README"

  # openWakeWord ships NO model binaries in its wheel. Every Model() builds an
  # AudioFeatures, which loads melspectrogram.onnx + embedding_model.onnx from
  # the package's own resources/models directory — fetched separately, at
  # runtime. Without them the ears raise NO_SUCHFILE and the start-atom
  # watchdog restarts them every 3 seconds forever.
  #
  # Passing a model name that matches no official model downloads ONLY the
  # shared feature + VAD models (~6 MB). Calling download_models() with no
  # arguments would additionally pull six unrelated wake models (alexa,
  # hey_jarvis, ...) that ATOM never uses.
  #
  # This lives here rather than beside the pip installs so that `--sync`
  # retries it — that is the documented recovery when the first install ran
  # offline. It is a no-op once the files are present.
  bold "openWakeWord feature models"
  ( [ -f "$APP_DIR/.venv/bin/activate" ] && . "$APP_DIR/.venv/bin/activate"
    python3 - <<'OWWEOF'
import openwakeword.utils as u
u.download_models(model_names=["hey_atom"])
from openwakeword.utils import AudioFeatures
AudioFeatures(inference_framework="onnx")
OWWEOF
  ) && ok "feature models present (melspectrogram + embedding)" \
    || warn "openWakeWord feature models unavailable — 'Hey ATOM' will NOT load until these download. With the Pi online, re-run: bash install.sh --sync"

  bold "Wake phrase: Hey ATOM"
  WW="$REPO_DIR/wakeword/hey_atom.onnx"; [ -f "$WW" ] || WW="$REPO_DIR/hey_atom.onnx"
  if [ -f "$WW" ]; then
    cp "$WW" "$APP_DIR/hey_atom.onnx"
    ok "hey_atom.onnx installed — physical microphone validation still required (VALIDATION.md Phase 2)"
  elif [ -f "$APP_DIR/hey_atom.onnx" ]; then
    ok "hey_atom.onnx present — physical microphone validation still required (VALIDATION.md Phase 2)"
  else
    echo
    echo "  ============================================="
    echo "   X  Hey ATOM model missing"
    echo "      WAKE WORD NOT READY"
    echo "  ============================================="
    echo "   Installation continues for development, but"
    echo "   voice wake is OFF until hey_atom.onnx exists."
    echo "   The touchscreen mic button works meanwhile."
    echo
    echo "   To create it (training time depends on results):"
    echo "     1. wakeword/README.md in the atom-pi repo — full pipeline"
    echo "     2. Record your dataset:  python record_dataset.py"
    echo "     3. Train via openWakeWord's Colab notebook (phrase: hey atom)"
    echo "     4. Validate:  python wakeword_validate.py hey_atom.onnx --data data/"
    echo "        (in a repo checkout that file is named validate_model.py)"
    echo "     5. Put hey_atom.onnx in the repo, then run:  bash install.sh --sync"
    echo "        (or simply: cp hey_atom.onnx ~/pocket-ai/ && sudo reboot)"
    echo "  ============================================="
    warn "WAKE WORD NOT READY (see banner above)"
  fi
}

# --sync / post-install re-run: refresh the ATOM layer only.
run_sync() {
  [ -d "$APP_DIR" ] || die "no install found at $APP_DIR — run the installer without --sync first."
  bold "==============================================="
  bold "  atom-pi sync — refreshing the ATOM layer only"
  bold "==============================================="
  resolve_repo_dir
  ok "Merge files at $REPO_DIR"
  install_atom_layer
  echo
  bold "Sync complete. Restart ATOM to pick it up:"
  echo "    sudo reboot        (or: bash $APP_DIR/atom-stop.sh, then the ATOM icon)"
  echo
  echo "  Health check:  cd $APP_DIR && python atom_doctor.py"
  exit 0
}


exec > >(tee -a "$LOG") 2>&1

# Explicit sync request. Placed after logging is wired up so the sync run is
# captured in $LOG like any other run.
if [ "${1:-}" = "--sync" ]; then
  run_sync
fi

echo
bold "==============================================="
bold "  atom-pi installer — stage $(get_stage)"
bold "==============================================="

# -----------------------------------------------------------------------------
# Stage 0: system update + firmware  (ends in reboot)
# -----------------------------------------------------------------------------
if [ "$(get_stage)" -eq 0 ]; then
  bold "[Stage 0] Updating the operating system and Pi firmware"
  sudo apt update || die "apt update failed — is the Pi online?"
  sudo apt full-upgrade -y || die "system upgrade failed"
  sudo rpi-eeprom-update -a || warn "eeprom update returned nonzero (often fine if already current)"
  ok "System updated"
  stage 1
  reboot_and_continue
fi

# -----------------------------------------------------------------------------
# Stage 1: PCIe Gen3 + verify BOTH Hailo and NVMe are visible
#          + make sure we're booted from the NVMe        (may end in reboot)
# -----------------------------------------------------------------------------
if [ "$(get_stage)" -eq 1 ]; then
  bold "[Stage 1] PCIe configuration and hardware check"

  if ! grep -q "dtparam=pciex1_gen=3" /boot/firmware/config.txt 2>/dev/null; then
    echo "dtparam=pciex1_gen=3" | sudo tee -a /boot/firmware/config.txt >/dev/null
    ok "PCIe Gen 3 enabled"
    stage 1   # stay on this stage; re-check after reboot
    reboot_and_continue
  fi
  ok "PCIe Gen 3 already enabled"

  HAILO_SEEN=$(lspci | grep -ci hailo || true)
  NVME_SEEN=$(lspci | grep -ci "non-volatile\|nvme" || true)
  if [ "${ATOM_SKIP_PCIE_CHECK:-0}" = "1" ]; then
    # Escape hatch for bring-up on partial hardware. NOT a supported build:
    # nothing downstream has been validated without the Hailo module and the
    # NVMe drive, and Stage 2 still installs the Hailo stack.
    warn "ATOM_SKIP_PCIE_CHECK=1 — skipping the Hailo/NVMe gate. UNSUPPORTED and untested; expect failures later."
  else
    [ "$HAILO_SEEN" -ge 1 ] || die "Hailo not detected on PCIe. Power off and check: ribbon cable seated+latched both ends, correct orientation, pogo/supplemental power connected, module screwed down flat. Then run the installer again. (To proceed anyway on partial hardware — unsupported — re-run with ATOM_SKIP_PCIE_CHECK=1.)"
    [ "$NVME_SEEN" -ge 1 ] || die "NVMe drive not detected on PCIe. Power off and reseat the SSD in its slot; check the board's supplemental power. Then run the installer again. (To proceed anyway on partial hardware — unsupported — re-run with ATOM_SKIP_PCIE_CHECK=1.)"
    ok "Hailo and NVMe both visible on PCIe"
  fi

  ROOTDEV=$(findmnt -n -o SOURCE /)
  if echo "$ROOTDEV" | grep -q nvme; then
    ok "Already booting from the NVMe drive"
    stage 2
  elif [ "${ATOM_ALLOW_SD:-0}" = "1" ]; then
    warn "ATOM_ALLOW_SD=1 — continuing from the microSD card (model loads will be slower)."
    stage 2
  else
    warn "You are still running from the microSD card."
    echo
    echo "  ONE manual step (it's a safe graphical tool):"
    echo "   1. Raspberry menu -> Accessories -> SD Card Copier"
    echo "   2. Copy From: the mmcblk0 device   Copy To: the nvme0n1 device"
    echo "   3. When it finishes, run:  sudo raspi-config"
    echo "      -> 6 Advanced Options -> Boot Order -> NVMe/USB Boot"
    echo "   4. Shut down, REMOVE the microSD card, power on"
    echo "   5. Run this installer again"
    echo
    echo "   Staying on the SD card on purpose? Re-run with ATOM_ALLOW_SD=1"
    echo "   to continue (slower model loads; everything else works)."
    echo
    # Deliberately NOT advancing the stage: the migration has not happened
    # yet, and recording stage 2 here would make the stage file claim
    # progress that does not exist — the re-run would skip this check
    # entirely whether or not the user did the copy.
    stage 1
    exit 0
  fi
fi

# -----------------------------------------------------------------------------
# Stage 2: Hailo software  (ends in reboot)
# -----------------------------------------------------------------------------
if [ "$(get_stage)" -eq 2 ]; then
  bold "[Stage 2] Installing the Hailo AI accelerator software"
  ROOTDEV=$(findmnt -n -o SOURCE /)
  echo "$ROOTDEV" | grep -q nvme || warn "Still on microSD — continuing, but do the SSD migration from Stage 1 for full speed."
  sudo apt install -y dkms || die "dkms install failed"
  sudo apt install -y hailo-all || die "hailo-all install failed"
  ok "Hailo software installed"
  stage 3
  reboot_and_continue
fi

# -----------------------------------------------------------------------------
# Stage 3: everything else — deps, app, models, merge  (long; no reboot)
# -----------------------------------------------------------------------------
if [ "$(get_stage)" -eq 3 ]; then
  bold "[Stage 3] Verifying Hailo"
  hailortcli fw-control identify >/dev/null 2>&1 \
    || die "Hailo software installed but the device didn't respond. Run 'hailortcli fw-control identify' to see the error, or re-run the installer to retry."
  ok "Hailo responding"

  bold "[Stage 3] System packages"
  sudo apt install -y portaudio19-dev python3-dev python3-pip python3-venv \
       python3-picamera2 rpicam-apps git curl alsa-utils \
       kiwix-tools poppler-utils || die "system packages failed"

  if ! command -v node >/dev/null || ! node -v | grep -q "^v2[0-9]"; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - || die "NodeSource setup failed"
    sudo apt install -y nodejs || die "Node.js install failed"
  fi
  ok "System packages ready (node $(node -v))"

  bold "[Stage 3] Getting this repo's merge files"
  resolve_repo_dir
  ok "Merge files at $REPO_DIR"

  bold "[Stage 3] Cloning pocket-ai"
  if [ -d "$APP_DIR" ] && [ "${UPDATE:-0}" = "1" ]; then
    BAK="$HOME/pocket-ai.bak-$(date +%Y%m%d-%H%M)"
    mv "$APP_DIR" "$BAK" && ok "previous install kept at $BAK (rollback = move it back)"
  fi
  if [ ! -d "$APP_DIR" ]; then
    git clone https://github.com/nazirlouis/pocket-ai.git "$APP_DIR" || die "pocket-ai clone failed"
    git -C "$APP_DIR" checkout "$POCKET_SHA" 2>/dev/null \
      && ok "pocket-ai pinned to verified commit ${POCKET_SHA:0:10}" \
      || warn "couldn't pin pocket-ai to $POCKET_SHA — using latest main (patches may print manual follow-ups)"
  fi
  # `set -e` is not in effect, so an unchecked cd would let every command
  # below run in the wrong directory.
  cd "$APP_DIR" || die "could not enter $APP_DIR"

  bold "[Stage 3] Python environment (this is the long one)"
  [ -d .venv ] || python3 -m venv --system-site-packages .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt || die "pip install of pocket-ai requirements failed"
  pip install "semantic-router[local]" onnxruntime tqdm websocket-client requests huggingface_hub \
    || die "pip install of merge dependencies failed"
  # openwakeword pinned. --no-deps avoids its tflite-runtime requirement,
  # which has no wheel for current Python and is only needed by the tflite
  # inference path — ATOM uses the ONNX path. But --no-deps ALSO drops the
  # deps that path genuinely needs, so install them explicitly:
  # scikit-learn is imported at module level by openwakeword/__init__.py
  # (custom_verifier_model), so without it `import openwakeword` raises
  # ModuleNotFoundError before any model is ever loaded.
  pip install --no-deps "openwakeword==0.6.0" || die "openwakeword install failed"
  pip install "scikit-learn>=1,<2" || die "scikit-learn (openwakeword dependency) install failed"
  ok "Python environment ready"

  bold "[Stage 3] Configuring ATOM (.env — verified: pocket-ai reads all of this from environment)"
  # Audio output: the USB speaker is ATOM's voice (the official DSI
  # touch display has no audio). USB first; HDMI only as a fallback —
  # the Pi lists HDMI audio even with nothing plugged in, so HDMI-first
  # would route sound to a nonexistent sink on this hardware.
  CARD=$(aplay -l 2>/dev/null | grep -im1 usb | grep -oP 'card \K\d+')
  [ -z "$CARD" ] && CARD=$(aplay -l 2>/dev/null | grep -m1 -oP 'card \K\d+(?=: vc4hdmi)')
  if [ -n "$CARD" ]; then TTS_DEV="plughw:${CARD},0"; else TTS_DEV="default"; warn "no USB/HDMI audio found yet — using ALSA default (edit TTS_ALSA_DEVICE in .env later)"; fi
  # Never silently discard hand-edited config. This stage re-runs whenever
  # anything later in it fails, and the installer itself tells users to edit
  # TTS_ALSA_DEVICE here — regenerating unconditionally threw that away.
  if [ -f .env ]; then
    cp .env ".env.bak-$(date +%Y%m%d-%H%M)"
    ok "existing .env kept (backup written) — delete .env and re-run to regenerate"
  else
  cat > .env <<ENVEOF
PORT=8000
TTS_ALSA_DEVICE=${TTS_DEV}
CHAT_REPO_ID=Qwen/Qwen3-4B-GGUF
CHAT_FILENAME=Qwen3-4B-Q4_K_M.gguf
WAKEWORD_ENGINE=openwakeword-onnx-0.6.0
WAKEWORD_MODEL=hey_atom.onnx
WAKEWORD_THRESHOLD=0.5
WAKEWORD_COOLDOWN=2
LISTEN_SECONDS=6
CAMERA_ON_WAKE=1
BARGE_IN=1
WAKE_THRESHOLD_BARGE=0.7
LOG_FILE=atom.log
ATOM_VERSION=1.0.0-rc2
POCKET_SHA=${POCKET_SHA}
BMA_SHA=${BMA_SHA}
ATOM_LIBRARY_PATH=
KIWIX_PORT=8090
ENVEOF
  ok ".env written (audio: ${TTS_DEV}, brain: Qwen3-4B Q4_K_M)"
  fi

  bold "[Stage 3] Pre-downloading the main brain (Qwen3-4B, ~2.5GB)"
  python - <<'PY' || { warn "Qwen3-4B pre-download failed — the backend retries at first start; if it still fails, set CHAT_REPO_ID/CHAT_FILENAME in .env to a Qwen3-4B Q4_K_M GGUF you can access, or delete those lines to fall back to the stock 0.6B model."; }
from huggingface_hub import hf_hub_download
hf_hub_download("Qwen/Qwen3-4B-GGUF", "Qwen3-4B-Q4_K_M.gguf", local_dir="models")
print("downloaded")
PY

  bold "[Stage 3] Downloading ATOM's voice (British, into models/ where PocketAudio looks)"
  mkdir -p models "$APP_DIR/sounds"
  for f in en_GB-alan-medium.onnx en_GB-alan-medium.onnx.json; do
    [ -f "models/$f" ] || curl -fL -o "models/$f" \
      "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/$f" \
      || warn "voice file $f failed — README covers the manual route; ATOM falls back to the default US voice"
  done

  bold "[Stage 3] Installing Ollama + Moondream (visual reasoning)"
  command -v ollama >/dev/null || curl -fsSL https://ollama.com/install.sh | sh \
    || warn "Ollama install failed — 'what do you see' answers won't work until installed"
  command -v ollama >/dev/null && ollama pull moondream || warn "moondream pull failed — retry later: ollama pull moondream"

  bold "[Stage 3] Optional feedback sounds (from be-more-agent, MIT)"
  BMA_TMP="$(mktemp -d)"
  if git clone https://github.com/brenpoly/be-more-agent.git "$BMA_TMP/bma" 2>/dev/null && git -C "$BMA_TMP/bma" checkout "$BMA_SHA" 2>/dev/null && [ -d "$BMA_TMP/bma/sounds" ]; then
    cp -r "$BMA_TMP/bma/sounds/." "$APP_DIR/sounds/"
    FIRST_ACK=$(find "$APP_DIR/sounds" -path "*ack*" -name "*.wav" | head -n1)
    [ -n "$FIRST_ACK" ] && cp "$FIRST_ACK" "$APP_DIR/sounds/ack.wav"
    ok "wake chime + thinking sounds installed"
  else
    warn "couldn't fetch feedback sounds — ATOM works silently on wake (drop any short ack.wav into sounds/ later)"
  fi
  rm -rf "$BMA_TMP"   # clean up on the failure path too

  install_atom_layer

  bold "[Stage 3] Building the touchscreen app"
  cd "$APP_DIR/chat-gui" || die "could not enter $APP_DIR/chat-gui — did the pocket-ai clone succeed?"
  npm install || die "npm install failed"
  ok "GUI built"

  stage 4
fi

# -----------------------------------------------------------------------------
# Stage 4: autostart + finish
# -----------------------------------------------------------------------------
if [ "$(get_stage)" -eq 4 ]; then
  bold "[Stage 4] Setting up autostart"
  mkdir -p "$HOME/.config/autostart"
  cat > "$APP_DIR/start-atom.sh" <<EOF
#!/usr/bin/env bash
cd "$APP_DIR"
source .venv/bin/activate
set -a; [ -f .env ] && . ./.env; set +a
echo "===== ATOM-Pi startup self-check ====="
python atom_doctor.py || true
echo "======================================"
( until python app.py; do echo "[watchdog] backend exited — restarting in 3s"; sleep 3; done ) &
# Wait for the backend to actually answer instead of guessing at 25s. On a
# cold first boot model loading can take far longer than that, and the ears
# would previously start talking to a backend that wasn't up yet.
echo "waiting for the backend to come up..."
# PORT comes from .env, sourced above. Hardcoding 8000 here meant that
# changing PORT made this loop wait the full three minutes and then start
# the ears against a backend it had decided was down.
ATOM_HEALTH="http://localhost:\${PORT:-8000}/health"
for _i in \$(seq 1 90); do
  curl -sf "\$ATOM_HEALTH" >/dev/null 2>&1 && break
  sleep 2
done
if curl -sf "\$ATOM_HEALTH" >/dev/null 2>&1; then
  echo "backend is up."
else
  echo "backend still not answering after 3 minutes — starting the rest anyway; check atom.log"
fi
if [ -f hey_atom.onnx ]; then
  ( until python wakeword_listener.py; do echo "[watchdog] ears exited — restarting in 3s"; sleep 3; done ) &
else
  echo "(wake word off: hey_atom.onnx not present — mic button works)"
fi
cd chat-gui
until npm run dev; do echo "[watchdog] GUI exited — restarting in 3s"; sleep 3; done
EOF
  chmod +x "$APP_DIR/start-atom.sh"
  cat > "$HOME/.config/autostart/atom.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ATOM
Exec=lxterminal -e $APP_DIR/start-atom.sh
Path=$APP_DIR
EOF
  mkdir -p "$HOME/Desktop" 2>/dev/null || true
  cp "$HOME/.config/autostart/atom.desktop" "$HOME/Desktop/" 2>/dev/null \
    || warn "couldn't place the ATOM desktop icon (autostart still works)"
  cat > "$APP_DIR/atom-stop.sh" <<'EOSTOP'
#!/usr/bin/env bash
# Leave ATOM mode: free the Pi for normal desktop use (browser, files,
# downloads, terminal). Suspends camera + AI subsystems; double-click
# the ATOM icon (or reboot) to return. The OS itself is never locked.
curl -s -X POST http://localhost:8000/camera/stop >/dev/null 2>&1
pkill -f wakeword_listener.py 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
pkill -f electron 2>/dev/null
pkill -f "python app.py" 2>/dev/null
echo "ATOM suspended — the desktop is all yours. Double-click ATOM to bring it back."
EOSTOP
  chmod +x "$APP_DIR/atom-stop.sh"
  cat > "$HOME/Desktop/atom-desktop-mode.desktop" <<EOF2
[Desktop Entry]
Type=Application
Name=ATOM — Desktop Mode
Exec=lxterminal -e $APP_DIR/atom-stop.sh
Path=$APP_DIR
EOF2
  ok "ATOM will start on boot (and via the desktop icon)"
  stage 5

  echo
  bold "==============================================="
  bold "  DONE. Reboot the Pi and ATOM starts itself."
  bold "==============================================="
  echo "  First launch downloads a few remaining models — give it"
  echo "  several quiet minutes, then say: \"Hey ATOM\""
  echo "  (if the installer noted hey_atom.onnx was missing, the wake word"
  echo "   is off until you add it — the touchscreen mic works meanwhile)"
  echo
  echo "  Health check any time:  cd ~/pocket-ai && python atom_doctor.py"
  echo "  Speaker/mic calibration: add --sound or --mic"
  echo "  Install log saved to: $LOG"
  exit 0
fi

# -----------------------------------------------------------------------------
# Already installed: re-running is a SYNC, not a no-op. This is the path that
# picks up a hey_atom.onnx trained after the fact, and any updated ATOM module.
# Previously this printed "already completed" and did nothing, which made the
# installer's own "drop in hey_atom.onnx and re-run" instruction a dead end.
# -----------------------------------------------------------------------------
bold "Installer already completed (stage $(get_stage)) — syncing the ATOM layer."
echo "  (Nothing is re-downloaded. For a genuine full re-run: rm $STAGE_FILE)"
echo
run_sync
