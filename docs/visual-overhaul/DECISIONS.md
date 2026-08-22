# Visual overhaul — decisions log

One entry per visual decision, with the reason. Newest last.

## D1 — Single GL layer, not per-element material shaders
**Decision:** one `<canvas>` behind the DOM hosting the ambient field,
the orb and hero-panel glass, with a single fullscreen post shader.
**Why:** WebGL cannot sample DOM content, so per-element refraction of
live UI is not achievable without moving those surfaces into GL and
re-implementing them — which would break "keep buttons and operations".
One context also means one place to spend the Pi's limited fill rate.
**Cost:** glass refracts the ambient field, not the text behind it. Said
plainly rather than implied.

## D2 — CRT grade composites *under* the text layer
**Decision:** grain, chromatic aberration and curvature apply to the GL
layer only; DOM text sits above them, ungraded.
**Why:** the UI's type is `Press Start 2P` at 10–14px. A 1px RGB split
on a 1px-stem pixel font is illegibility, not atmosphere. The brief's
own rule — legibility beats spectacle — forces this.

## D3 — "Reduced" quality tier is the accessibility variant
**Decision:** the no-GL, token-only path serves three jobs at once:
Reduced tier, `prefers-reduced-motion` / `prefers-reduced-transparency`,
and the automatic fallback when the device misses frame rate.
**Why:** one well-tested static path beats three half-tested ones, and it
guarantees the app is fully usable if the GPU work has to be switched off.
