#!/usr/bin/env python3
"""
ATOM-Pi patcher — applies the merge to a cloned pocket-ai tree.

Every edit below targets an EXACT string verified in the real source
(commit inspected during the ATOM-Pi audit). If upstream changes and
an anchor no longer matches, the patch prints a manual fallback and
the installer continues — warnings are follow-ups, not failures.

Patches:
  1. chat_ai.py  : British voice   PocketAudio() -> PocketAudio(model_name=...)
  2. chat_ai.py  : ATOM personality replaces both hardcoded system prompts
  3. tool_ai.py  : append describe_scene runner + TOOL_RUNNERS registration
  4. tools.json  : register the describe_scene tool schema
  5. semantic_router_ai.py : scene questions -> function_gemma route
  6. Home.jsx    : render the full ATOM robot via the adapter
  7. chat_ai.py  : abort also clears the TTS queue (barge-in)
  8. chat_ai.py  : real seeing / knowledge_search / web_search / tool_use states
  9. app.py      : bind the backend to localhost, not every interface
 10. app.py      : mount the ATOM library API router
 11. App.jsx     : register the /library route
 12. Home.jsx    : ATOM hub — title, VOICE/CHAT/VISION/LIBRARY, DESKTOP
 13. main+preload: DESKTOP tile runs atom-stop.sh over IPC
 14. index.css   : load the ATOM visual system (tokens + compat layer)
 15. App.jsx     : mount the GL backdrop + /dev/shader-lab route
(The audio output device needs no patch: it's the TTS_ALSA_DEVICE
environment variable, which the installer writes into .env.)
"""

import json
import sys
from pathlib import Path

APP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "pocket-ai"
WARN = []
def warn(m): WARN.append(m); print(f"  [!!] {m}")
def ok(m): print(f"  [ok] {m}")

# ---- 1 & 2: chat_ai.py -----------------------------------------------------
chat = APP / "chat_ai.py"
if chat.exists():
    t = chat.read_text()

    # 1. Voice: exact anchor `self.tts = PocketAudio()`
    if 'PocketAudio(model_name=' in t:
        ok("voice already set")
    elif "self.tts = PocketAudio()" in t:
        t = t.replace("self.tts = PocketAudio()",
                      'self.tts = PocketAudio(model_name="en_GB-alan-medium")')
        ok("voice -> en_GB-alan-medium (files pre-placed in models/)")
    else:
        warn("PocketAudio() anchor not found — set model_name in chat_ai.py "
             "manually to 'en_GB-alan-medium'.")

    # 2. Personality: replace both hardcoded system prompts.
    # Read once at import via pathlib, with a fallback: the previous form
    # (`open(...).read()`) leaked a file handle on every system-prompt build,
    # re-read from disk each time, used a POSIX-only rsplit on __file__, and
    # took the backend down entirely if personality.txt was ever missing.
    P = '_ATOM_PERSONALITY'
    PREAMBLE = (
        "\n# --- ATOM-Pi merge: personality loaded once, never fatal ---\n"
        "from pathlib import Path as _AtomPath\n"
        "try:\n"
        "    _ATOM_PERSONALITY = (_AtomPath(__file__).parent / 'personality.txt').read_text().strip()\n"
        "except Exception:\n"
        "    _ATOM_PERSONALITY = 'You are a helpful assistant. Keep your responses concise for text-to-speech.'\n"
    )
    a1 = '"You are a helpful assistant. Keep your responses concise for text-to-speech."'
    a2 = '"You are a helpful assistant."'
    n = 0
    if a1 in t: t = t.replace(a1, P); n += 1
    if a2 in t: t = t.replace(a2, P); n += 1
    if n and "_ATOM_PERSONALITY =" not in t:
        # Insert the loader after the file's opening import block so the name
        # is defined before any use, and after the module docstring so that
        # docstring stays a docstring.
        lines = t.splitlines(keepends=True)
        insert_at, seen_import = 0, False
        for i, line in enumerate(lines[:80]):
            if line.startswith(("import ", "from ")):
                seen_import, insert_at = True, i + 1
            elif seen_import and line.strip() and not line.startswith((" ", ")", "\t")):
                break
        lines.insert(insert_at, PREAMBLE)
        t = "".join(lines)
    if "_ATOM_PERSONALITY" in t and n:
        ok(f"ATOM personality wired into {n} system prompt(s)")
    elif "_ATOM_PERSONALITY" in t:
        ok("personality already wired")
    else:
        warn("system-prompt anchors not found — point the system prompts in "
             "chat_ai.py at personality.txt manually.")
    chat.write_text(t)
else:
    warn("chat_ai.py missing — has pocket-ai's layout changed?")

# ---- 3: tool_ai.py — safe end-of-file append -------------------------------
tool = APP / "tool_ai.py"
if tool.exists():
    t = tool.read_text()
    if "describe_scene" in t:
        ok("tool_ai already dispatches describe_scene")
    elif "TOOL_RUNNERS" in t:
        # Each ATOM tool is registered independently and behind its own guard.
        # A bare module-level import here would take the WHOLE tool registry
        # down if one optional dependency were missing — losing every stock
        # pocket-ai tool because, say, Ollama's client wasn't installed.
        t += (
            "\n\n# --- ATOM-Pi merge: vision + local-library tools ---\n"
            "# Registered defensively: a missing optional dependency disables\n"
            "# only its own tool, never the rest of TOOL_RUNNERS.\n"
            "import logging as _atom_logging\n"
            "try:\n"
            "    from vision_describe import describe_scene as _atom_describe\n"
            "    def run_describe_scene(arguments: dict) -> str:\n"
            "        return _atom_describe((arguments or {}).get('question', ''))\n"
            "    TOOL_RUNNERS['describe_scene'] = run_describe_scene\n"
            "except Exception as _atom_exc:\n"
            "    _atom_logging.warning('ATOM: describe_scene unavailable (%s)', _atom_exc)\n"
            "try:\n"
            "    from atom_knowledge import search_library as _atom_lib, compare_sources as _atom_cmp\n"
            "    def run_search_library(arguments: dict) -> str:\n"
            "        return _atom_lib((arguments or {}).get('query', ''))\n"
            "    def run_compare_sources(arguments: dict) -> str:\n"
            "        return _atom_cmp((arguments or {}).get('query', ''))\n"
            "    TOOL_RUNNERS['search_library'] = run_search_library\n"
            "    TOOL_RUNNERS['compare_sources'] = run_compare_sources\n"
            "except Exception as _atom_exc:\n"
            "    _atom_logging.warning('ATOM: library tools unavailable (%s)', _atom_exc)\n"
        )
        tool.write_text(t)
        ok("describe_scene appended to TOOL_RUNNERS")
    else:
        warn("TOOL_RUNNERS registry not found in tool_ai.py — register "
             "run_describe_scene manually (see README).")
else:
    warn("tool_ai.py missing.")

# ---- 4: tools.json ----------------------------------------------------------
tj = APP / "tools.json"
ENTRY = {
    "name": "describe_scene",
    "description": ("Look through the camera and describe the scene in natural "
                    "language. Use when the user asks what you see, what "
                    "something looks like, or who is there."),
    "parameters": {"type": "object", "properties": {"question": {
        "type": "string", "description": "The user's question about the scene"}},
        "required": []},
}
LIB_ENTRY = {"name": "search_library",
    "description": ("Search the user's LOCAL offline library on the USB drive "
                    "(Kiwix, books, PDFs, documents). Use when the user says "
                    "library, kiwix, my books, my documents, or offline knowledge."),
    "parameters": {"type": "object", "properties": {"query": {
        "type": "string", "description": "What to look up"}}, "required": ["query"]}}
CMP_ENTRY = {"name": "compare_sources",
    "description": ("Answer using BOTH the local library and a live web search, "
                    "labeled separately. Use when the user asks to compare local "
                    "knowledge with what's online."),
    "parameters": {"type": "object", "properties": {"query": {
        "type": "string", "description": "What to compare"}}, "required": ["query"]}}
if tj.exists():
    try:
        data = json.loads(tj.read_text())
        lst = data if isinstance(data, list) else data.setdefault("tools", [])
        names = {x.get("name") for x in lst if isinstance(x, dict)}
        added = []
        for e in (ENTRY, LIB_ENTRY, CMP_ENTRY):
            if e["name"] not in names:
                lst.append(e); added.append(e["name"])
        if added:
            tj.write_text(json.dumps(data, indent=2))
            ok("tools.json gained: " + ", ".join(added))
        else:
            ok("tools.json already has all ATOM tools")
    except Exception as e:
        warn(f"tools.json edit failed ({e}) — add the entry by hand (README).")
else:
    warn("tools.json missing.")

# ---- 5: router — verified anchor: the web-search utterance line -------------
router = APP / "semantic_router_ai.py"
SCENES = ('            "what do you see", "describe what is in front of you",\n'
          '            "who is in the room", "what am I holding", "look at this",\n'
          '            "what does my library say about python", "search my kiwix library",\n'
          '            "look in my local books", "search my documents for recipes",\n'
          '            "compare my local library with what is online",\n')
if router.exists():
    t = router.read_text()
    if "what do you see" in t:
        ok("router already has scene utterances")
    else:
        anchor = '"scan my local network", "scan the network",'
        if anchor in t:
            t = t.replace(anchor, anchor + "\n" + SCENES.rstrip("\n"))
            router.write_text(t)
            ok("scene utterances added to function_gemma route")
        else:
            warn("router anchor not found — add scene questions to the "
                 "function_gemma utterances list by hand.")
else:
    warn("semantic_router_ai.py missing.")

# ---- 6: GUI — swap Avatar for the full ATOM robot (verified anchor) ---------
home = APP / "chat-gui" / "src" / "renderer" / "src" / "components" / "Home.jsx"
if home.exists():
    t = home.read_text()
    if "AtomRobotAdapter" in t:
        ok("Home.jsx already renders the ATOM robot")
    elif "import Avatar from './Avatar';" in t:
        t = t.replace("import Avatar from './Avatar';",
                      "import Avatar from './AtomRobotAdapter';")
        home.write_text(t)
        ok("Home.jsx now renders the full ATOM robot (via adapter)")
    else:
        warn("Home.jsx Avatar import anchor not found — import AtomRobotAdapter "
             "and render <AtomRobot state={voiceStatus}/> manually.")
else:
    warn("Home.jsx missing — wire AtomRobot into the GUI manually (README).")

# ---- 7: barge-in server side — abort also silences the TTS queue -----------
if chat.exists():
    t = chat.read_text()
    A = 'logger.info("Global Abort Requested")\n                abort_event.set()'
    if "clear_queue()" in t and "Global Abort" in t and "atom barge-in" in t:
        ok("abort already clears TTS")
    elif A in t:
        t = t.replace(A, A + "\n                try:  # atom barge-in\n"
                             "                    ai.tts.clear_queue()\n"
                             "                except Exception:\n"
                             "                    pass")
        chat.write_text(t)
        ok("abort now also clears the TTS queue (barge-in)")
    else:
        warn("abort-handler anchor not found — add ai.tts.clear_queue() "
             "inside the 'abort' command branch of /ws/voice manually.")

# ---- 8: real SEEING / KNOWLEDGE_SEARCH / WEB_SEARCH / TOOL_USE states ---
if chat.exists():
    t = chat.read_text()
    A = ('await websocket.send_json({"type": "ai_start"})\n'
         '        await websocket.send_json({"type": "voice_status", "status": "thinking"})')
    if '"knowledge_search"' in t:
        ok("seeing/knowledge/web/tool states already wired")
    elif A in t:
        NEW = ('await websocket.send_json({"type": "ai_start"})\n'
               '        _status = "thinking"  # atom: real capability states\n'
               '        if route == "function_gemma":\n'
               '            _low = text.lower()\n'
               '            if any(k in _low for k in ("see", "look", "holding", "in front", "who is", "describe", "camera")):\n'
               '                _status = "seeing"\n'
               '            elif any(k in _low for k in ("library", "kiwix", "my books", "my documents", "offline knowledge")):\n'
               '                _status = "knowledge_search"\n'
               '            elif any(k in _low for k in ("search", "weather", "news", "price", "online", "web", "latest")):\n'
               '                _status = "web_search"\n'
               '            else:\n'
               '                _status = "tool_use"\n'
               '        await websocket.send_json({"type": "voice_status", "status": _status})')
        t = t.replace(A, NEW)
        chat.write_text(t)
        ok("voice path now reports seeing / knowledge_search / web_search / tool_use")
    else:
        warn("voice-status anchor not found — the robot will show 'thinking' "
             "for vision/search/tool requests (cosmetic only).")

# ---- 9: app.py — bind the backend to localhost ------------------------------
# Upstream serves on 0.0.0.0, which publishes the API AND the /captures mount
# — the stills describe_scene takes — to every device on the network, with no
# authentication. Every ATOM caller (wakeword_listener, vision_describe,
# atom_doctor, atom-stop.sh) uses localhost, and the Electron GUI runs on the
# Pi itself, so nothing loses access. Deliberate LAN exposure stays possible
# via ATOM_BIND_HOST, but it is now opt-in rather than the default.
app_py = APP / "app.py"
if app_py.exists():
    t = app_py.read_text()
    A = 'uvicorn.run(app, host="0.0.0.0", port=PORT)'
    NEW = ('uvicorn.run(app, host=os.environ.get("ATOM_BIND_HOST", "127.0.0.1"), '
           'port=PORT)  # atom: localhost by default; set ATOM_BIND_HOST=0.0.0.0 to expose')
    if "ATOM_BIND_HOST" in t:
        ok("backend already bound to localhost")
    elif A in t:
        if "import os" not in t:
            warn("app.py binds 0.0.0.0 but does not import os — change the "
                 "host in uvicorn.run() to \"127.0.0.1\" by hand.")
        else:
            app_py.write_text(t.replace(A, NEW))
            ok("backend now binds 127.0.0.1 (camera captures no longer served to the LAN)")
    else:
        warn("uvicorn.run anchor not found — check app.py binds 127.0.0.1, not "
             "0.0.0.0, or the camera captures are reachable from the network.")
else:
    warn("app.py missing — cannot verify the backend's bind address.")

# ---- 10: app.py — mount the ATOM library API -------------------------------
# Guarded so a missing atom_library_api (or a missing dependency inside it)
# costs only the LIBRARY screen, never the whole backend.
if app_py.exists():
    t = app_py.read_text()
    A = "app.include_router(chat_router)"
    if "atom_library_api" in t:
        ok("library API already mounted")
    elif A in t:
        app_py.write_text(t.replace(A, A + "\n\n"
            "# --- ATOM-Pi merge: USB knowledge library over HTTP ---\n"
            "try:\n"
            "    from atom_library_api import router as _atom_library_router\n"
            "    app.include_router(_atom_library_router)\n"
            "except Exception as _atom_exc:\n"
            "    logger.warning('ATOM: library API unavailable (%s)', _atom_exc)"))
        ok("library API mounted at /library")
    else:
        warn("app.include_router anchor not found — add "
             "'app.include_router(atom_library_api.router)' to app.py by hand; "
             "the LIBRARY screen will 404 until you do.")

# ---- 11: App.jsx — register the /library route -----------------------------
app_jsx = APP / "chat-gui" / "src" / "renderer" / "src" / "App.jsx"
if app_jsx.exists():
    t = app_jsx.read_text()
    IMP = "import GPIOControl from './components/GPIOControl';"
    RTE = '        <Route path="/gpio" element={<GPIOControl />} />'
    if "AtomLibrary" in t:
        ok("/library route already registered")
    elif IMP in t and RTE in t:
        t = t.replace(IMP, IMP + "\nimport AtomLibrary from './components/AtomLibrary';")
        t = t.replace(RTE, RTE + '\n        <Route path="/library" element={<AtomLibrary />} />')
        app_jsx.write_text(t)
        ok("/library route registered")
    else:
        warn("App.jsx route anchors not found — import AtomLibrary and add "
             '<Route path="/library" element={<AtomLibrary />} /> by hand.')
else:
    warn("App.jsx missing — cannot register the LIBRARY screen.")

# ---- 12: Home.jsx — the ATOM hub -------------------------------------------
# Title becomes ATOM, and the menu becomes what this robot actually does:
# VOICE (already wired in the backend, works without a wake word), CHAT,
# VISION, LIBRARY — with DESKTOP set apart because it LEAVES ATOM.
if home.exists():
    t = home.read_text()
    ICONS_OLD = ("import { MessageCircle, Settings, Camera, "
                 "Image as GalleryIcon, Code } from 'lucide-react';")
    ICONS_NEW = ("import { MessageCircle, Settings, Camera, BookOpen, Mic, "
                 "Monitor } from 'lucide-react';")
    TITLE_OLD = "                    POCKET AI\n"
    TITLE_NEW = "                    ATOM\n"
    GRID_OLD = """            {/* Main Menu Grid - 4 buttons: Chat, Vision, Agent, Gallery */}
            <div className="grid grid-cols-2 grid-rows-[1fr_1fr] gap-3 z-10 w-full max-w-[520px] flex-1 min-h-0">
                <MenuButton icon={MessageCircle} label="CHAT" onClick={() => navigate('/chat')} color="var(--pixel-primary)" />
                <MenuButton icon={Camera} label="VISION" onClick={() => navigate('/camera')} color="var(--pixel-accent)" />
                <MenuButton icon={Code} label="AGENT" onClick={() => navigate('/tasks')} color="#f7768e" />
                <MenuButton icon={GalleryIcon} label="GALLERY" onClick={() => navigate('/gallery')} color="var(--pixel-secondary)" />
            </div>"""
    GRID_NEW = """            {/* ATOM hub - 4 capability tiles */}
            <div className="grid grid-cols-2 grid-rows-[1fr_1fr] gap-3 z-10 w-full max-w-[520px] flex-1 min-h-0">
                <MenuButton icon={Mic} label="VOICE" onClick={() => toggleVoice()} color="var(--pixel-accent)" />
                <MenuButton icon={MessageCircle} label="CHAT" onClick={() => navigate('/chat')} color="var(--pixel-primary)" />
                <MenuButton icon={Camera} label="VISION" onClick={() => navigate('/camera')} color="#f7768e" />
                <MenuButton icon={BookOpen} label="LIBRARY" onClick={() => navigate('/library')} color="var(--pixel-secondary)" />
            </div>

            {/* DESKTOP is deliberately not one of the tiles above: those are
                things ATOM does, this one leaves ATOM and hands the Pi back. */}
            <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => window.electron?.desktopMode?.()}
                className="pixel-btn mt-3 w-full max-w-[520px] min-h-[56px] text-[12px] z-10 flex-none"
                style={{ borderColor: 'var(--at-edge-base)', color: 'var(--at-text-mid)' }}
            >
                <Monitor size={22} />
                <span>DESKTOP</span>
            </motion.button>"""
    if "LIBRARY" in t and "desktopMode" in t:
        ok("ATOM hub already in place")
    elif ICONS_OLD in t and TITLE_OLD in t and GRID_OLD in t:
        t = t.replace(ICONS_OLD, ICONS_NEW).replace(TITLE_OLD, TITLE_NEW).replace(GRID_OLD, GRID_NEW)
        home.write_text(t)
        ok("hub: ATOM title + VOICE/CHAT/VISION/LIBRARY + DESKTOP")
    else:
        missing = [n for n, a in (("icons", ICONS_OLD), ("title", TITLE_OLD),
                                  ("menu grid", GRID_OLD)) if a not in t]
        warn("Home.jsx hub anchors not found (" + ", ".join(missing) + ") — the "
             "robot still renders, but the menu keeps pocket-ai's stock tiles.")

# ---- 13: DESKTOP tile over Electron IPC ------------------------------------
pre = APP / "chat-gui" / "src" / "preload" / "index.js"
if pre.exists():
    t = pre.read_text()
    A = "const electronAPI = {\n    quit: () => ipcRenderer.send('app-quit')\n}"
    if "desktopMode" in t:
        ok("preload already exposes desktopMode")
    elif A in t:
        pre.write_text(t.replace(A,
            "const electronAPI = {\n"
            "    quit: () => ipcRenderer.send('app-quit'),\n"
            "    // atom: leave ATOM mode, hand the Pi back to the desktop\n"
            "    desktopMode: () => ipcRenderer.send('atom-desktop-mode')\n}"))
        ok("preload exposes window.electron.desktopMode()")
    else:
        warn("preload electronAPI anchor not found — the DESKTOP tile will do "
             "nothing until desktopMode is exposed by hand.")
else:
    warn("preload/index.js missing — DESKTOP tile cannot be wired.")

main_js = APP / "chat-gui" / "src" / "main" / "index.js"
if main_js.exists():
    t = main_js.read_text()
    IMP = "import { join } from 'path'"
    A = "    ipcMain.on('app-quit', () => app.quit())"
    if "atom-desktop-mode" in t:
        ok("main process already handles desktop mode")
    elif IMP in t and A in t:
        t = t.replace(IMP, IMP + "\n"
            "// --- ATOM-Pi merge: DESKTOP tile runs atom-stop.sh ---\n"
            "import { spawn } from 'child_process'\n"
            "import { existsSync } from 'fs'\n"
            "import { homedir } from 'os'\n"
            "import { resolve as _atomResolve } from 'path'")
        t = t.replace(A, A + "\n\n"
            "    // atom-stop.sh suspends the camera, ears, backend and this GUI,\n"
            "    // so it deliberately kills us. Spawn it detached to outlive us.\n"
            "    ipcMain.on('atom-desktop-mode', () => {\n"
            "        try {\n"
            "            const candidates = [\n"
            "                process.env.ATOM_STOP_SCRIPT,\n"
            "                _atomResolve(process.cwd(), '..', 'atom-stop.sh'),\n"
            "                _atomResolve(homedir(), 'pocket-ai', 'atom-stop.sh')\n"
            "            ].filter(Boolean)\n"
            "            const script = candidates.find((c) => existsSync(c))\n"
            "            if (!script) {\n"
            "                console.warn('ATOM: atom-stop.sh not found; staying in ATOM mode')\n"
            "                return\n"
            "            }\n"
            "            spawn('bash', [script], { detached: true, stdio: 'ignore' }).unref()\n"
            "        } catch (e) {\n"
            "            console.warn('ATOM: desktop mode failed', e)\n"
            "        }\n"
            "    })")
        main_js.write_text(t)
        ok("DESKTOP tile wired to atom-stop.sh")
    else:
        warn("main/index.js anchors not found — the DESKTOP tile will do nothing.")
else:
    warn("main/index.js missing — DESKTOP tile cannot be wired.")

# ---- 14: index.css — load the visual system --------------------------------
# atom-visual.css redefines the seven --pixel-* variables and the four
# .pixel-* utility classes in terms of the new ramps, which is what re-skins
# every existing surface without editing a single component. It must load
# AFTER tailwind so its overrides win the cascade.
css = APP / "chat-gui" / "src" / "renderer" / "src" / "index.css"
if css.exists():
    t = css.read_text()
    FONTS_OLD = ("@import url('https://fonts.googleapis.com/css2?"
                 "family=Press+Start+2P&family=VT323&display=swap');")
    FONTS_NEW = ("@import url('https://fonts.googleapis.com/css2?"
                 "family=Chakra+Petch:wght@400;500;600;700&"
                 "family=IBM+Plex+Mono:wght@400;500;600&display=swap');")
    if "atom-visual.css" in t:
        ok("visual system already loaded")
    elif '@import "tailwindcss";' in t:
        # The font @import must stay the FIRST rule in the file: CSS drops an
        # @import that follows any other rule, so it cannot live in
        # atom-visual.css (which is itself imported after tailwind).
        if FONTS_OLD in t:
            t = t.replace(FONTS_OLD, FONTS_NEW)
        else:
            warn("index.css font @import not found — Chakra Petch / IBM Plex "
                 "Mono will fall back to system faces.")
        css.write_text(t.replace('@import "tailwindcss";',
                                 '@import "tailwindcss";\n@import "./atom-visual.css";'))
        ok("index.css loads the ATOM visual system (fonts swapped)")
    else:
        warn("index.css tailwind import not found — add "
             "'@import \"./atom-visual.css\";' after the tailwind import by hand.")
else:
    warn("index.css missing — the visual system will not load.")

# ---- 15: App.jsx — GL backdrop + shader lab --------------------------------
if app_jsx.exists():
    t = app_jsx.read_text()
    IMP = "import AtomLibrary from './components/AtomLibrary';"
    MOUNT = "            <StatusBar />"
    RTE = '        <Route path="/library" element={<AtomLibrary />} />'
    if "AtomBackdropLive" in t:
        ok("GL backdrop already mounted")
    elif IMP in t and MOUNT in t and RTE in t:
        t = t.replace(IMP, IMP
            + "\nimport { AtomBackdropLive } from './components/AtomBackdrop';"
            + "\nimport AtomShaderLab from './components/AtomShaderLab';")
        # Inside WebSocketProvider so the field reacts to real voice_status,
        # and before StatusBar so it sits behind every surface.
        t = t.replace(MOUNT, "            <AtomBackdropLive />\n" + MOUNT)
        t = t.replace(RTE, RTE + '\n        <Route path="/dev/shader-lab" element={<AtomShaderLab />} />')
        app_jsx.write_text(t)
        ok("GL backdrop mounted + /dev/shader-lab registered")
    else:
        warn("App.jsx backdrop anchors not found — the token layer still "
             "applies, but the GL field and shader lab will be absent.")

print()
if WARN:
    print(f"Patching finished with {len(WARN)} manual follow-up(s) above. "
          "ATOM runs without them; each unlocks one feature.")
else:
    print("All patches applied cleanly against verified anchors.")
