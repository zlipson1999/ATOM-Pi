#!/usr/bin/env python3
"""
atom_doctor — ATOM-Pi diagnostics, calibration, backup, and logs.

  python atom_doctor.py            hardware + software check table
  python atom_doctor.py --sound    speaker test (say yes if you hear it)
  python atom_doctor.py --mic      record 3s, play it back
  python atom_doctor.py --backup   save .env/personality/wake model/chats
  python atom_doctor.py --logs     tail the backend log
  python atom_doctor.py --version  version record (ATOM, models, pins, OS)

Run from ~/pocket-ai. Every line reports OK / DEGRADED / MISSING, and
the summary is READY only when nothing required is missing.
"""
import json, os, shutil, subprocess, sys, tarfile, time, urllib.request
from pathlib import Path

APP = Path(__file__).parent
def sh(cmd): 
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20).stdout
    except Exception: return ""
def row(name, status, note=""):
    mark = {"OK":"[ OK ]","DEGRADED":"[ !! ]","MISSING":"[MISS]"}[status]
    print(f"  {mark} {name:<22} {note}")
    return status

def checks():
    print("ATOM-Pi Hardware & Software Check\n" + "=" * 46)
    results = []
    model = Path("/proc/device-tree/model").read_text(errors="ignore") if Path("/proc/device-tree/model").exists() else ""
    results.append(row("Raspberry Pi", "OK" if "Raspberry Pi 5" in model else "DEGRADED", model.strip("\x00") or "not a Pi?"))
    thr = sh("vcgencmd get_throttled").strip()
    results.append(row("Cooling/power", "OK" if "0x0" in thr else "DEGRADED", thr or "vcgencmd unavailable"))
    tmp = sh("vcgencmd measure_temp").strip()
    if tmp: print(f"         temperature: {tmp}")
    root = sh("findmnt -n -o SOURCE /").strip()
    results.append(row("Boot drive", "OK" if "nvme" in root else "DEGRADED", root + ("" if "nvme" in root else " (SD card — slower)")))
    hail = sh("hailortcli fw-control identify 2>/dev/null")
    results.append(row("Hailo accelerator", "OK" if "Board" in hail or "Hailo" in hail else "MISSING", "detection off if missing"))
    results.append(row("Microphone", "OK" if "card" in sh("arecord -l") else "MISSING"))
    results.append(row("Speaker", "OK" if "card" in sh("aplay -l") else "MISSING"))
    results.append(row("Wake model", "OK" if (APP/"hey_atom.onnx").exists() else "MISSING",
                       "present — mic validation per VALIDATION.md still required" if (APP/"hey_atom.onnx").exists() else "'Hey ATOM' off — mic button works"))
    voice = (APP/"models/en_GB-alan-medium.onnx").exists()
    results.append(row("Voice model", "OK" if voice else "DEGRADED", "" if voice else "falls back to default US voice"))
    brain = any((APP/"models").glob("*.gguf")) if (APP/"models").exists() else False
    results.append(row("Brain model (GGUF)", "OK" if brain else "MISSING", "" if brain else "downloads at first start"))
    oll = sh("ollama list 2>/dev/null")
    results.append(row("Vision (Moondream)", "OK" if "moondream" in oll else "MISSING", "'what do you see' needs it"))
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=3) as r:
            ok = json.load(r).get("status") == "ok"
    except Exception: ok = False
    results.append(row("Backend", "OK" if ok else "MISSING", "" if ok else "start it: bash start-atom.sh"))
    results.append(row("Config (.env)", "OK" if (APP/".env").exists() else "DEGRADED"))
    try:
        urllib.request.urlopen("https://one.one.one.one", timeout=3)
        results.append(row("Internet", "OK", "ONLINE"))
    except Exception:
        results.append(row("Internet", "DEGRADED", "OFFLINE — local capabilities continue"))
    try:
        sys.path.insert(0, str(APP))
        from atom_knowledge import status as _lib_status
        st = _lib_status()
        results.append(row("Local library", "OK" if "LIBRARY: /" in st else "DEGRADED", ("optional — " if "LIBRARY: /" not in st else "") + st.replace("LIBRARY: ", "")))
    except Exception as e:
        results.append(row("Local library", "DEGRADED", f"module unavailable: {e}"))
    free = shutil.disk_usage("/").free // 2**30
    results.append(row("Disk free", "OK" if free > 8 else "DEGRADED", f"{free} GB"))
    print("=" * 46)
    if "MISSING" in results: print("  STATUS: DEGRADED — items above are missing")
    elif "DEGRADED" in results: print("  STATUS: READY (with notes above)")
    else: print("  STATUS: READY (bench check — physical validation per VALIDATION.md still applies)")

def sound():
    dev = os.environ.get("TTS_ALSA_DEVICE", "default")
    print(f"Playing test tone on {dev} — you should hear 'front left/right'...")
    subprocess.run(f"speaker-test -D {dev} -c 2 -t wav -l 1", shell=True)

def mic():
    print("Recording 3 seconds — say: 'Can you hear me, ATOM?'")
    subprocess.run("arecord -d 3 -f cd /tmp/atom_mic_test.wav", shell=True)
    dev = os.environ.get("TTS_ALSA_DEVICE", "default")
    print("Playing it back...")
    subprocess.run(f"aplay -D {dev} /tmp/atom_mic_test.wav", shell=True)

def backup():
    out = Path.home() / f"atom-backup-{time.strftime('%Y%m%d-%H%M')}.tgz"
    with tarfile.open(out, "w:gz") as t:
        for f in [".env", "personality.txt", "hey_atom.onnx", "conversations.json", "tools.json"]:
            if (APP/f).exists(): t.add(APP/f, arcname=f)
    print(f"Backup written: {out}\nRestore: extract into ~/pocket-ai after reinstalling.")

def logs():
    lf = APP / os.environ.get("LOG_FILE", "atom.log")
    print(sh(f"tail -n 60 {lf}") or f"(no log at {lf} yet)")

def version():
    env = {}
    if (APP/".env").exists():
        for line in (APP/".env").read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1); env[k.strip()] = v.strip()
    osrel = ""
    if Path("/etc/os-release").exists():
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME"): osrel = line.split("=",1)[1].strip('"')
    print("ATOM-Pi version record")
    print("  ATOM-Pi:        ", env.get("ATOM_VERSION", "unknown"))
    print("  OS:             ", osrel or "unknown")
    print("  pocket-ai pin:  ", env.get("POCKET_SHA", "unknown"))
    print("  be-more pin:    ", env.get("BMA_SHA", "unknown"))
    print("  Brain model:    ", env.get("CHAT_FILENAME", "stock default"))
    print("  Wake model:     ", "hey_atom.onnx" if (APP/"hey_atom.onnx").exists() else "NOT INSTALLED")
    print("  Voice model:    ", "en_GB-alan-medium" if (APP/"models/en_GB-alan-medium.onnx").exists() else "stock default")
    print("  Vision model:   ", "moondream (ollama)" )
    print("  Hailo runtime:  ", (sh("hailortcli --version").strip() or "not detected"))

if __name__ == "__main__":
    a = sys.argv[1:] or [""]
    {"--sound": sound, "--mic": mic, "--backup": backup,
     "--logs": logs, "--version": version}.get(a[0], checks)()
