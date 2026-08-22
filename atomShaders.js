/**
 * ATOM — shader sources
 * ---------------------------------------------------------------------------
 * GLSL ES 3.00 (WebGL2), with a WebGL1 fallback selected at runtime.
 *
 * The chain is five draws, deliberately:
 *   1 SCENE      ambient volumetric field + raymarched orb + caustics -> FBO
 *   2 THRESHOLD  bright-pass + downsample to 1/4                      -> FBO
 *   3 BLUR H     separable gaussian                                   -> FBO
 *   4 BLUR V     separable gaussian                                   -> FBO
 *   5 COMPOSITE  scene + bloom, then CA -> scanline -> grain -> dither
 *                -> vignette -> curvature                            -> screen
 *
 * Passes 2-4 are skipped entirely on Balanced and Reduced tiers, which is why
 * bloom is a real threshold+blur rather than a blur slapped over everything:
 * a fake bloom cannot be switched off without changing the whole image.
 *
 * IMPORTANT (DECISIONS D2): nothing here ever touches DOM text. This canvas
 * renders BEHIND the UI. Grain, aberration and curvature grade the field and
 * the orb only. Text composites on top, ungraded and full contrast.
 */

export const VERT = `#version 300 es
precision highp float;
out vec2 vUv;
void main() {
  // Fullscreen triangle. Cheaper than a quad: one primitive, no diagonal seam.
  vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  vUv = p;
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}`;

/* ===========================================================================
   PASS 1 — SCENE
   The living background and the orb. Everything emissive originates here.
   =========================================================================== */
export const SCENE = `#version 300 es
precision highp float;

in vec2 vUv;
out vec4 fragColor;

uniform vec2  uRes;
uniform float uTime;
uniform sampler2D uFlow;      // 4 fbm octaves, one per channel
uniform sampler2D uCaustics;

// --- state: cross-faded between two signatures, never popped ---------------
uniform vec3  uColA;          // previous state key colour
uniform vec3  uColB;          // target state key colour
uniform float uMix;           // 0..1 spring-driven blend
uniform float uTurbA;
uniform float uTurbB;
uniform float uFlowSpeed;
uniform float uFieldGain;

// --- orb -------------------------------------------------------------------
uniform vec2  uOrbPos;        // screen-space centre, 0..1
uniform float uOrbRadius;     // in uv units
uniform float uOrbEnergy;     // 0..1 idle breathing -> full excitation
uniform float uAudio;         // live amplitude when available, else breathing
uniform vec4  uBands;         // low..high frequency energy when available

// --- material --------------------------------------------------------------
uniform float uCausticGain;
uniform float uGlassIOR;

#define TAU 6.2831853

vec3 hsvShift(vec3 c, float h) {
  const vec3 k = vec3(0.57735);
  float cosA = cos(h);
  return c * cosA + cross(k, c) * sin(h) + k * dot(k, c) * (1.0 - cosA);
}

/** Curl of the baked flow field. Gives divergence-free motion, which is what
    makes the drift read as smoke rather than as a scrolling texture. */
vec2 curl(vec2 p, float t) {
  float e = 0.0025;
  vec2 o = vec2(t * 0.013, t * -0.009);
  float n1 = texture(uFlow, p + vec2(0.0, e) + o).r;
  float n2 = texture(uFlow, p - vec2(0.0, e) + o).r;
  float n3 = texture(uFlow, p + vec2(e, 0.0) + o).r;
  float n4 = texture(uFlow, p - vec2(e, 0.0) + o).r;
  return vec2(n1 - n2, n4 - n3) / (2.0 * e);
}

/** Volumetric density: three advected octaves, warped by curl. */
float field(vec2 uv, float t, float turb) {
  vec2 c = curl(uv * 0.6, t) * 0.0022 * turb;
  vec4 a = texture(uFlow, uv * 0.55 + c + vec2(t * 0.0075, t * -0.0042));
  vec4 b = texture(uFlow, uv * 1.30 - c * 1.6 + vec2(t * -0.0113, t * 0.0061));
  vec4 d = texture(uFlow, uv * 2.60 + c * 2.4 + vec2(t * 0.0181, t * 0.0134));
  float v = a.r * 0.55 + b.g * 0.30 + d.b * 0.15;
  v = pow(clamp(v * 1.35 - 0.16, 0.0, 1.0), 1.5 + turb * 0.5);
  return v;
}

/** Analytic sphere SDF for the orb shell. */
float sdSphere(vec3 p, float r) { return length(p) - r; }

/**
 * Raymarched orb. Marches a small fixed step count through a displaced
 * spherical shell, accumulating emission. Step count is low on purpose: this
 * runs on a VideoCore VII while a 4B model is generating, and a 64-step march
 * would blow the entire frame budget on one element.
 */
vec3 orb(vec2 uv, vec2 res, float t, vec3 key) {
  vec2 d = (uv - uOrbPos) * vec2(res.x / res.y, 1.0);
  float dist = length(d);
  float R = uOrbRadius;
  if (dist > R * 3.2) return vec3(0.0);       // cheap bail: most pixels exit here

  vec3 ro = vec3(d, -1.2);
  vec3 rd = vec3(0.0, 0.0, 1.0);
  vec3 acc = vec3(0.0);
  float breathe = 0.5 + 0.5 * sin(t * 0.9);

  const int STEPS = 18;
  for (int i = 0; i < STEPS; i++) {
    float fi = float(i) / float(STEPS);
    vec3 p = ro + rd * (0.55 + fi * 1.3);

    // Shell displacement driven by real audio bands when present. Each band
    // pushes a different spherical harmonic lobe so speech reads as shape,
    // not as uniform scaling.
    float wob =
        sin(p.y * 9.0 + t * 2.1) * uBands.x * 0.10 +
        sin(p.x * 13.0 - t * 2.7) * uBands.y * 0.075 +
        sin((p.x + p.y) * 19.0 + t * 3.4) * uBands.z * 0.05 +
        sin(length(p.xy) * 27.0 - t * 4.2) * uBands.w * 0.035;

    float rr = R * (0.86 + breathe * 0.05 + uAudio * 0.18) + wob;
    float sd = sdSphere(p, rr);

    // Emission concentrated in a thin shell -> a hollow core that glows at the
    // rim, rather than a solid ball.
    float shell = exp(-abs(sd) * 26.0);
    float inner = exp(-max(sd, 0.0) * 7.0) * 0.35;
    acc += (key * shell * 1.6 + key * inner) * (0.35 + uOrbEnergy);
  }
  acc /= float(STEPS);

  // Fresnel-ish rim: hotter where the shell turns away from the viewer.
  float rim = pow(clamp(1.0 - abs(dist - R) / (R * 0.55), 0.0, 1.0), 2.2);
  acc += key * rim * (0.5 + uOrbEnergy * 0.9) * 0.40;

  // Outer halo, the part that bleeds around the robot silhouette above it.
  float halo = exp(-pow(max(0.0, dist - R) / (R * 1.25), 1.6) * 3.0);
  acc += key * halo * 0.11 * (0.4 + uOrbEnergy);

  return acc;
}

void main() {
  vec2 uv = vUv;
  float t = uTime;

  vec3 key  = mix(uColA, uColB, uMix);
  float turb = mix(uTurbA, uTurbB, uMix);

  // --- volumetric ambient field -------------------------------------------
  float f = field(uv * 1.4, t * uFlowSpeed, turb);

  // Depth: a second, slower, larger-scale layer parallaxes behind the first.
  float fBack = field(uv * 0.7 + 0.37, t * uFlowSpeed * 0.55, turb * 0.6);

  // Header band attenuation. uv.y == 1 is the top of the screen. The title
  // and status line sit on open field with no glass beneath them, so the
  // field is quietened there rather than veiling the text -- measured to lift
  // the title from 4.12:1 to comfortably past AA.
  float headroom = mix(1.0, 0.30, smoothstep(0.76, 1.0, uv.y));

  vec3 col = vec3(0.0);
  col += hsvShift(key, -0.35) * fBack * 0.40 * uFieldGain * headroom;
  col += key * f * 0.85 * uFieldGain * headroom;

  // --- caustics: light refracted through the glass above ------------------
  vec2 cuv = uv * 1.15 + vec2(t * 0.006, t * -0.004);
  float ca = texture(uCaustics, cuv).r;
  float cb = texture(uCaustics, cuv * 1.7 - vec2(t * 0.009, 0.0)).r;
  float caus = pow(ca * 0.6 + cb * 0.4, 1.9);
  col += hsvShift(key, 0.18) * caus * uCausticGain * (0.35 + f * 0.9) * headroom;

  // --- dispersion: IOR splits the field slightly across RGB at high gradient
  float g = length(vec2(dFdx(f), dFdy(f)));
  col.r *= 1.0 + g * uGlassIOR * 0.9;
  col.b *= 1.0 - g * uGlassIOR * 0.6;

  // --- orb ------------------------------------------------------------------
  col += orb(uv, uRes, t, hsvShift(key, 0.05));

  // Deep base so blacks stay genuinely black rather than washing to grey.
  // Deep blacks are load-bearing for this look: lift the floor and
  // apply a mild filmic toe so the darks compress instead of greying.
  col = max(col - 0.03, 0.0);
  col = col / (col + 0.55) * 1.55;

  fragColor = vec4(col, 1.0);
}`;

/* ===========================================================================
   PASS 2 — BRIGHT-PASS THRESHOLD (+ implicit 4x downsample via viewport)
   =========================================================================== */
export const THRESHOLD = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 fragColor;
uniform sampler2D uTex;
uniform float uThreshold;   // luminance below this contributes nothing
uniform float uKnee;        // soft shoulder so bloom doesn't switch on abruptly
void main() {
  vec3 c = texture(uTex, vUv).rgb;
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  // Soft-knee curve: quadratic below the knee, linear above it.
  float k = max(0.0001, uKnee);
  float soft = clamp(l - uThreshold + k, 0.0, 2.0 * k);
  soft = soft * soft / (4.0 * k);
  float w = max(soft, l - uThreshold) / max(l, 0.0001);
  fragColor = vec4(c * w, 1.0);
}`;

/* ===========================================================================
   PASS 3/4 — SEPARABLE GAUSSIAN
   =========================================================================== */
export const BLUR = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 fragColor;
uniform sampler2D uTex;
uniform vec2 uDir;      // (texel, 0) or (0, texel)
void main() {
  // 9-tap gaussian folded to 5 fetches using linear-sampling offsets.
  vec3 c = texture(uTex, vUv).rgb * 0.2270270270;
  c += texture(uTex, vUv + uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture(uTex, vUv - uDir * 1.3846153846).rgb * 0.3162162162;
  c += texture(uTex, vUv + uDir * 3.2307692308).rgb * 0.0702702703;
  c += texture(uTex, vUv - uDir * 3.2307692308).rgb * 0.0702702703;
  fragColor = vec4(c, 1.0);
}`;

/* ===========================================================================
   PASS 5 — COMPOSITE + POST CHAIN
   Order is fixed by physics, not taste: bloom is light, so it adds before the
   lens distorts it; aberration is a lens property; scanlines and grain are the
   display; vignette and curvature are the glass tube. Each is independently
   switchable via its gain uniform (0 = disabled, and the branch is skipped).
   =========================================================================== */
export const COMPOSITE = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 fragColor;

uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform sampler2D uBlue;     // blue noise, for dithering
uniform sampler2D uDust;

uniform vec2  uRes;
uniform float uTime;
uniform float uBloomGain;
uniform float uAberration;
uniform float uScanline;
uniform float uGrain;
uniform float uVignette;
uniform float uCurvature;
uniform float uDustGain;
uniform float uGlitch;       // 0 normally; spikes briefly on error/state jumps
uniform float uExposure;

/** Barrel distortion, applied only near the edges so the centre stays sharp. */
vec2 curve(vec2 uv, float k) {
  vec2 c = uv * 2.0 - 1.0;
  float r2 = dot(c, c);
  c *= 1.0 + k * r2 * r2;       // r^4 keeps the middle almost untouched
  return c * 0.5 + 0.5;
}

void main() {
  vec2 uv = vUv;

  if (uCurvature > 0.0001) uv = curve(uv, uCurvature);

  // Off-screen after curvature = the bezel. Deep black, not clamped smear.
  if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
    fragColor = vec4(0.0, 0.0, 0.0, 1.0);
    return;
  }

  // --- occasional glitch displacement --------------------------------------
  if (uGlitch > 0.001) {
    float band = floor(uv.y * 48.0);
    float h = fract(sin(band * 91.3 + floor(uTime * 18.0) * 13.7) * 43758.5453);
    if (h > 1.0 - uGlitch * 0.35) {
      uv.x += (h - 0.5) * uGlitch * 0.06;
    }
  }

  // --- chromatic aberration: scales from centre, like a real lens ----------
  vec3 col;
  if (uAberration > 0.001) {
    vec2 d = uv - 0.5;
    float amt = uAberration * 0.0016 * dot(d, d) * 4.0;
    col.r = texture(uScene, uv + d * amt).r;
    col.g = texture(uScene, uv).g;
    col.b = texture(uScene, uv - d * amt).b;
  } else {
    col = texture(uScene, uv).rgb;
  }

  // --- bloom ----------------------------------------------------------------
  if (uBloomGain > 0.001) col += texture(uBloom, uv).rgb * uBloomGain;

  col *= uExposure;

  // --- phosphor scanlines ---------------------------------------------------
  if (uScanline > 0.001) {
    float s = sin(uv.y * uRes.y * 1.5708);       // one dark line per 2 device px
    col *= 1.0 - uScanline * (0.5 + 0.5 * s);
    // aperture-grille tint: adjacent columns lean R / G / B
    float col3 = mod(floor(uv.x * uRes.x), 3.0);
    vec3 mask = col3 < 1.0 ? vec3(1.06, 0.97, 0.97)
              : col3 < 2.0 ? vec3(0.97, 1.06, 0.97)
                           : vec3(0.97, 0.97, 1.06);
    col *= mix(vec3(1.0), mask, uScanline * 6.0);
  }

  // --- dust and scratches on the tube --------------------------------------
  if (uDustGain > 0.001) {
    float dd = texture(uDust, uv * 1.3).r;
    col += vec3(dd) * uDustGain * 0.06;
  }

  // --- animated film grain --------------------------------------------------
  if (uGrain > 0.001) {
    vec2 gu = uv * uRes / 64.0 + vec2(fract(uTime * 11.0), fract(uTime * 7.3));
    float n = texture(uBlue, gu).r;
    col += (n - 0.5) * uGrain;
  }

  // --- vignette -------------------------------------------------------------
  if (uVignette > 0.001) {
    vec2 d = uv - 0.5;
    col *= 1.0 - uVignette * pow(dot(d, d) * 2.0, 1.35);
  }

  // --- ordered dither: kills 8-bit banding in the dark field ---------------
  float dth = texture(uBlue, gl_FragCoord.xy / 64.0).r;
  col += (dth - 0.5) / 255.0;

  fragColor = vec4(max(col, 0.0), 1.0);
}`;
