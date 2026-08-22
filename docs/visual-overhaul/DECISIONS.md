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

## D4 — The seven `--pixel-*` variables are the delivery mechanism
**Decision:** rather than restyle 24 components, redefine pocket-ai's seven CSS
variables and four `.pixel-*` utility classes in terms of the new ramps.
**Why:** every component already styles through them. One file re-skins chat,
camera, gallery, tasks, GPIO, settings, keyboard and library at once — without
editing a component, touching a handler, or moving a button. It is the only
approach that satisfies "only the UI changes" while still being total.
**Cost:** chrome gets the language at whatever intensity those base values
encode; hero surfaces opt into more with `.at-glass` / `.at-emissive`.

## D5 — The pixel-art identity is retired
**Decision:** `Press Start 2P` / `VT323` out, `Chakra Petch` / `IBM Plex Mono` in.
**Why:** liquid glass and 1px-stem bitmap type are opposing languages — hard
4px borders and flat offset shadows against refraction and Fresnel falloff.
They cannot blend; one had to win. Confirmed with the user before proceeding.

## D6 — Bloom is a real threshold-and-blur, so it can be switched off
**Decision:** four extra draws (bright-pass, downsample, blur H, blur V) rather
than a cheap blur composited over everything.
**Why:** a fake bloom cannot be disabled without changing the whole image, which
would make the Balanced and Reduced tiers look like a different design rather
than the same design turned down. Passes 2-4 are skipped entirely below High.

## D7 — Contrast is fixed at the source, never by veiling text
**Decision:** measured worst-frame contrast, then fixed the two causes: a
denser glass backing (`--at-surface-legible`, 0.62 alpha) under anything
carrying text, and an in-shader attenuation of the field under the header band.
**Why:** the first pass measured five AA failures — CHAT at 2.58:1, DESKTOP at
1.51:1, the title at 4.12:1. Dropping a scrim over the text would have hidden
the field; quietening the field where text lives keeps both. All seven probed
regions now pass, worst case 5.89:1.
**Measured, not estimated:** 30 sampled frames, glyphs hidden so the background
is what is actually sampled.

## D8 — DESKTOP's quietness comes from size, not from dim colour
**Decision:** the `#565f89` label became `--at-text-mid`.
**Why:** it measured 1.51:1. A control that is quiet because it is unreadable is
not quiet, it is broken. Hierarchy now comes from smaller type and a plain
border rather than from failing contrast.

## D9 — The calibrator may soften the look, never delete it
**Decision:** automatic downgrade bottoms out at `balanced`. Only a principled
reason reaches `reduced`: no WebGL2, a software renderer, or the user asking
for reduced motion/transparency.
**Why:** `reduced` tears the canvas down completely. A transient run of slow
frames — which on this device means "the 4B model is mid-response" — must not
be able to silently remove the entire visual identity. At `balanced` the field,
the orb and the grade all survive; only bloom and render resolution give way.
