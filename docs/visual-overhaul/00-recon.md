# Visual overhaul — Phase 0 recon

Written before any implementation. Everything below is read from the
repository and the pinned upstream checkout of `pocket-ai` at
`137fc627`. Where a number could not be measured on the real device, it
says so rather than guessing.

---

## 1. Stack map

| Question | Answer |
|---|---|
| Framework | React **19.2**, `react-router-dom` **7.13** (HashRouter, so it works from `file://`) |
| Shell | **Electron 40.4** — Chromium-based, Linux/arm64 on the Pi |
| Build | **electron-vite 5** over **Vite 7.3**, three targets: `main`, `preload`, `renderer` |
| Styling | **Tailwind CSS 4.1** via `@tailwindcss/vite` (no `tailwind.config.js` — v4 CSS-first config) |
| Animation | **framer-motion 12.34**, plus 2 hand-written `@keyframes` in `index.css` |
| Icons | `lucide-react` (SVG) |
| Markdown | `react-markdown` + `remark-gfm` (chat messages) |
| **Render surface** | **DOM only.** Zero `<canvas>`, zero WebGL, zero WebGPU, no three.js — verified by grep across the whole renderer |
| Design tokens | `src/renderer/src/index.css` — **7 CSS variables** (`--pixel-bg`, `-surface`, `-primary`, `-secondary`, `-accent`, `-text`, `-border`), Tokyo Night palette. Plus 4 utility classes (`.pixel-btn`, `.pixel-input`, `.pixel-select`, `.pixel-card`) |
| Fonts | `Press Start 2P` (headings/labels) and `VT323` (body), from Google Fonts |
| Window | `BrowserWindow` 480×800, `fullscreen: true`, `frame: false`, touch events enabled |

### The single most important structural fact

**There is no render surface to put shaders on.** The UI is DOM, SVG and
CSS end to end. "A persistent full-surface shader layer behind the UI"
is not an enhancement to the current architecture — it is the
introduction of a rendering architecture this app does not have.

That is doable, but it changes the honest description of this work from
"restyle" to "add a GPU compositing layer under an existing DOM app."

---

## 2. UI surface inventory

Routes are registered in `App.jsx`. `StatusBar` renders above every
route. **Hero** = surfaces the user actually looks at; **chrome** =
everything else.

### Hero

| Surface | File | Why hero |
|---|---|---|
| **ATOM robot** | `AtomRobot.jsx` (ATOM-owned) | The centrepiece. Hand-authored SVG, 11 states, arm-to-head thinking gesture, pulsing chest core. This is the "voice/attention orb" in the brief's terms — it already exists and already animates |
| **Hub / home screen** | `Home.jsx` (patched) | First and most-returned-to screen. Title, robot, 4 capability tiles, DESKTOP bar |
| **Chat conversation** | `MessageList.jsx`, `MessageBubble.jsx` | Where text is read at length. Legibility-critical |
| **Chat input** | `ChatInput.jsx` | Constant interaction target |
| **Camera / vision** | `CameraView.jsx` | Live video — a surface where post-processing is most tempting and most risky |
| **Status bar** | `StatusBar.jsx` | Always visible, 28px tall, tiny type |

### Chrome

`ChatHeader`, `ChatSidebar`, `ConnectionBar`, `CloseButton`,
`ErrorMessage`, `ErrorBoundary`, `LoadingSpinner`, `MiniChat`,
`Settings`, `Gallery`, `TaskManager`, `TaskAdd`, `HeartbeatManager`,
`GPIOControl`, `VirtualKeyboard`, `AtomLibrary` (ATOM-owned).

`VirtualKeyboard` deserves a note: it is a full on-screen keyboard
overlay, the only text-entry method on the device. It must stay fast and
unambiguous — it is the worst possible place for refraction or motion.

### Existing visual-effect load (the baseline we are adding to)

Counted across the renderer: `shadow-*` ×56, `transition-*` ×36,
`opacity-*` ×24, `animate-pulse` ×9, `backdrop-blur` ×7,
`animate-bounce` ×5, `blur-*` ×3, `animate-spin` ×2. `Avatar.jsx` alone
has 17 `motion.*` elements (it is replaced by `AtomRobot` in the ATOM
build, which uses CSS transforms and `setInterval`, not framer-motion).

So the app is *already* doing compositor work on every frame, before
anything in this brief is added.

---

## 3. Performance baseline

### Target hardware (from `README.md`, `BUILD.md`, `index.html` parts list)

- **Raspberry Pi 5, 16GB** — GPU is **VideoCore VII**, driven by the
  open `V3D` Mesa driver.
- **Hailo-8L 13 TOPS** on PCIe — an NPU for object detection. It cannot
  run graphics shaders; it is not a GPU in the sense this brief needs.
- **Official Raspberry Pi Touch Display 2, 10"**, DSI, no audio.

### Resolution is unknown and it matters

`BrowserWindow` is configured `480×800` but with `fullscreen: true`, so
the real framebuffer is the panel's native resolution, not 480×800.
Shader cost scales linearly with pixel count, so this is a first-order
input to every budget below. **It must be read off the device**
(`xrandr` or `wlr-randr`) before any shader work is sized.

### The contention problem

The GPU is not the only thing under load. On this one SoC, at the same
time, ATOM runs:

- **Qwen3-4B Q4_K_M** inference via `llama-cpp-python` (CPU, memory-bandwidth hungry)
- **Whisper** (`faster-whisper`) and/or **Vosk** for speech-to-text
- **Piper** for text-to-speech
- **Moondream** via Ollama for vision
- **Hailo** object detection
- **kiwix-serve** when the library is in use
- Electron itself, plus the Vite dev server (`start-atom.sh` runs `npm run dev`, not a production build)

The visually richest moments the brief asks for — `thinking`,
`speaking`, `seeing` — are **exactly** the moments the CPU and memory
bus are most saturated. Frame budget and inference load peak together.

### Honest statement of the baseline

**No baseline has been measured, because no Pi is present in this
environment.** Measuring it in a desktop browser here would be
misleading: different GPU, different driver, different resolution,
none of the competing AI workloads.

What must be measured on the device, before Phase 1:

```bash
# 1. Actual framebuffer resolution
wlr-randr || xrandr

# 2. Does Chromium even have hardware acceleration on this build?
#    (chrome://gpu inside the Electron devtools)

# 3. Current frame timing, idle and during inference
#    devtools Performance panel, 10s capture, at rest and mid-response

# 4. Thermals under sustained load
vcgencmd measure_temp; vcgencmd get_throttled
```

`atom_doctor.py` already reports throttling and temperature and can
carry the last two.

---

## 4. Where the brief and the hardware disagree

These are conflicts to resolve before implementation, not objections.

1. **"60fps on mid-tier integrated graphics."** A Pi 5's VideoCore VII
   is well below mid-tier integrated. Treating "mid-tier integrated" as
   the floor would set a target the device cannot meet. The real target
   should be *60fps on Pi 5 at panel-native resolution, while a 4B model
   is generating* — a much harder and much more useful bar.

2. **"Refractive surfaces with real distortion of what's behind them."**
   In a DOM app, what is behind a panel is *DOM* — live text, video,
   SVG. WebGL cannot sample DOM. Real refraction requires the refracted
   content to live inside the GL context. Three honest options:
   (a) glass refracts only the ambient field, not UI content;
   (b) move whole surfaces into WebGL and re-implement them (huge, and
   breaks "keep buttons and operations");
   (c) fake it with `backdrop-filter` (already used ×7) — cheap, and not
   what the brief means. **I recommend (a)** and will say so plainly in
   the design rather than implying real refraction.

3. **Post-processing versus a pixel font.** The UI's type is
   `Press Start 2P` at 10–14px. Chromatic aberration, grain, and barrel
   curvature applied over that will destroy it — a 1px RGB split on a
   1px-stem pixel font is not a stylistic choice, it is illegibility.
   The brief already says legibility wins. So the CRT grade must be
   **composited under the text layer, not over it**, or masked away
   from text. This is a real architectural constraint, not a tuning knob.

4. **Per-element material shaders.** Same root cause as (2). Feasible for
   a handful of hero surfaces that we draw in GL ourselves; not feasible
   as a general material system for DOM components.

5. **Dev server in production.** `start-atom.sh` runs `npm run dev`.
   Vite dev builds are unminified with HMR active. Before optimising
   shaders it is worth knowing whether the shipped path should be
   `npm run build` + a static load, which is free performance.

---

## 5. Proposed plan

Ordered so the cheapest, highest-certainty value lands first, and the
riskiest work is only attempted once we know it fits.

**Phase 0.5 — measure on device (blocking).**
Resolution, GPU acceleration status, idle and under-load frame timing,
thermals. Without these, every budget below is a guess.

**Phase 1 — tokens, no GPU.**
Replace the 7 flat variables with a real token layer: colour ramps,
elevation, blur radii, glow intensity, grain amount, motion curves and
durations, plus quality-tier and reduced-motion switches. Rewire every
component to read tokens. **This alone will visibly lift the app** and
carries essentially no performance risk. It is also the part that
survives even if the GPU layer proves too expensive.

**Phase 2 — one GL layer, not many.**
A single `<canvas>` behind the DOM, drawing: the volumetric ambient
field (fbm/curl flow, state-reactive), the ATOM orb, and the glass
backdrop for hero panels — all in one context, one pass. The post chain
runs as a single fullscreen shader with data-driven toggles, not
ping-pong passes. DOM UI composites on top, unaffected by the grade.

**Phase 3 — hero surfaces.**
Home/hub first, then chat, then camera. Chrome surfaces get tokens only.

**Phase 4 — motion language + shader lab.**
Springs in tokens; `/dev/shader-lab` route with live uniform sliders.

**Throughout:** quality tiers (Ultra/High/Balanced/Reduced) with the
Reduced tier being the token-only, no-GL path — which doubles as the
`prefers-reduced-motion` / `prefers-reduced-transparency` variant and
the automatic fallback if the device cannot hold frame rate.

### Explicitly out of scope

No logic changes. No refactors. Every button, route, handler and backend
call stays exactly as it is — the user's constraint, and the right one.
