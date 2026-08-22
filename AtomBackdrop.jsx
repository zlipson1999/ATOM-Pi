/**
 * ATOM — GL backdrop (ATOM-owned component)
 * ---------------------------------------------------------------------------
 * One WebGL2 canvas, fixed behind the entire DOM UI. Runs the five-pass chain
 * in atomShaders.js. This is the only GPU surface in the app; there are no
 * per-element material shaders, for the reason recorded in DECISIONS D1:
 * WebGL cannot sample DOM, so per-element refraction of live UI is not
 * achievable without moving those surfaces into GL and re-implementing them.
 *
 * It renders BEHIND everything (z-index 0, pointer-events none). It never
 * touches a button, a route or a handler. Text sits above it, ungraded.
 *
 * Quality tiers: ultra | high | balanced | reduced
 *   - chosen automatically from the GL renderer string, then corrected by
 *     measuring real frame times for the first two seconds
 *   - 'reduced' tears the canvas down completely and lets the CSS token layer
 *     carry the design on its own. That path is also what reduced-motion and
 *     reduced-transparency get, so it is a first-class design, not a failure
 *     mode (DECISIONS D3).
 */
import React, { useEffect, useRef, useState } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext.jsx';
import { VERT, SCENE, THRESHOLD, BLUR, COMPOSITE } from '../atomShaders.js';
import flowUrl from '../assets/atom/atom-flow.png';
import causticsUrl from '../assets/atom/atom-caustics.png';
import blueUrl from '../assets/atom/atom-bluenoise.png';
import dustUrl from '../assets/atom/atom-dust.png';

/* --- state signatures ------------------------------------------------------
   Each app state gets a distinct colour AND a distinct turbulence, so the
   field is readable as state even by someone who cannot distinguish the hues.
   Values are cross-faded by a spring; nothing ever pops. */
export const STATE_SIGNATURE = {
    boot:             { col: [0.10, 0.55, 0.85], turb: 1.5, energy: 0.75, speed: 1.5 },
    idle:             { col: [0.09, 0.42, 0.62], turb: 0.5, energy: 0.20, speed: 0.6 },
    listening:        { col: [0.16, 0.78, 0.95], turb: 1.0, energy: 0.62, speed: 1.1 },
    thinking:         { col: [0.42, 0.34, 0.95], turb: 2.1, energy: 0.90, speed: 1.9 },
    seeing:           { col: [0.20, 0.85, 0.78], turb: 1.3, energy: 0.70, speed: 1.3 },
    knowledge_search: { col: [0.55, 0.40, 0.95], turb: 1.5, energy: 0.72, speed: 1.4 },
    web_search:       { col: [0.25, 0.60, 1.00], turb: 1.7, energy: 0.74, speed: 1.6 },
    tool_use:         { col: [0.30, 0.70, 0.90], turb: 1.4, energy: 0.68, speed: 1.3 },
    speaking:         { col: [0.14, 0.86, 0.90], turb: 1.2, energy: 1.00, speed: 1.0 },
    error:            { col: [1.00, 0.28, 0.42], turb: 2.6, energy: 0.95, speed: 2.2 },
    offline:          { col: [0.22, 0.28, 0.36], turb: 0.2, energy: 0.06, speed: 0.25 }
};

const TIER_SCALE = { ultra: 1.0, high: 0.8, balanced: 0.6, reduced: 0 };
const TIER_BLOOM = { ultra: true, high: true, balanced: false, reduced: false };

function prefersReduced() {
    if (typeof window === 'undefined' || !window.matchMedia) return false;
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
        || window.matchMedia('(prefers-reduced-transparency: reduce)').matches;
}

/** First guess from the GPU string; corrected later by real frame timing. */
function guessTier(gl) {
    try {
        const dbg = gl.getExtension('WEBGL_debug_renderer_info');
        const r = (dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : '').toLowerCase();
        // V3D is the Pi's VideoCore. llvmpipe/swiftshader mean no GPU at all.
        if (/llvmpipe|softpipe|swiftshader/.test(r)) return 'reduced';
        if (/v3d|videocore|mali-g31|mali-g52/.test(r)) return 'balanced';
        if (/mali|adreno|intel|uhd|iris/.test(r)) return 'high';
        return 'ultra';
    } catch { return 'balanced'; }
}

export default function AtomBackdrop({ state = 'idle', orb = null, audio = 0, bands = null }) {
    const canvasRef = useRef(null);
    const [tier, setTier] = useState(() => (prefersReduced() ? 'reduced' : null));
    const stateRef = useRef(state);
    stateRef.current = state;
    const liveRef = useRef({ audio, bands, orb });
    liveRef.current = { audio, bands, orb };

    // Publish the tier so the CSS token layer can scale with it.
    useEffect(() => {
        if (tier) document.documentElement.setAttribute('data-at-quality', tier);
    }, [tier]);

    useEffect(() => {
        if (prefersReduced()) { setTier('reduced'); return; }
        const canvas = canvasRef.current;
        if (!canvas) return;

        let calibrateOff = false;
        const gl = canvas.getContext('webgl2', {
            alpha: false, antialias: false, depth: false, stencil: false,
            powerPreference: 'high-performance', preserveDrawingBuffer: false
        });
        if (!gl) { setTier('reduced'); return; }   // no WebGL2 -> token-only path

        // Manual pin wins over detection: lets the shader lab force a tier,
        // and lets someone on the Pi lock quality rather than let the
        // calibrator hunt. Cleared with localStorage.removeItem('atom-quality').
        let pinned = null;
        try { pinned = localStorage.getItem('atom-quality'); } catch { /* private mode */ }
        let quality = pinned && TIER_SCALE[pinned] !== undefined ? pinned : guessTier(gl);
        if (quality === 'reduced') { setTier('reduced'); return; }
        if (pinned) calibrateOff = true;
        setTier(quality);

        /* ---- gl helpers ---------------------------------------------------- */
        const compile = (type, src) => {
            const s = gl.createShader(type);
            gl.shaderSource(s, src); gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
                console.error('[ATOM shader]', gl.getShaderInfoLog(s));
                return null;
            }
            return s;
        };
        const program = (frag) => {
            const v = compile(gl.VERTEX_SHADER, VERT);
            const f = compile(gl.FRAGMENT_SHADER, frag);
            if (!v || !f) return null;
            const p = gl.createProgram();
            gl.attachShader(p, v); gl.attachShader(p, f); gl.linkProgram(p);
            if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
                console.error('[ATOM link]', gl.getProgramInfoLog(p)); return null;
            }
            const loc = {};
            const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
            for (let i = 0; i < n; i++) {
                const nm = gl.getActiveUniform(p, i).name.replace('[0]', '');
                loc[nm] = gl.getUniformLocation(p, nm);
            }
            return { p, loc };
        };

        const progScene = program(SCENE);
        const progThresh = program(THRESHOLD);
        const progBlur = program(BLUR);
        const progComp = program(COMPOSITE);
        if (!progScene || !progThresh || !progBlur || !progComp) { setTier('reduced'); return; }

        const vao = gl.createVertexArray();   // empty: the vertex shader is procedural

        const makeTarget = () => {
            const fb = gl.createFramebuffer();
            const tx = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, tx);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            return { fb, tx, w: 0, h: 0 };
        };
        const sizeTarget = (t, w, h) => {
            if (t.w === w && t.h === h) return;
            t.w = w; t.h = h;
            gl.bindTexture(gl.TEXTURE_2D, t.tx);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
            gl.bindFramebuffer(gl.FRAMEBUFFER, t.fb);
            gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t.tx, 0);
        };
        const tScene = makeTarget(), tA = makeTarget(), tB = makeTarget();

        const loadTex = (url, repeat) => {
            const tx = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, tx);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                new Uint8Array([12, 20, 34, 255]));
            const img = new Image();
            img.onload = () => {
                gl.bindTexture(gl.TEXTURE_2D, tx);
                gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
                const w = repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE;
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, w);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, w);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
            };
            img.src = url;
            return tx;
        };
        const texFlow = loadTex(flowUrl, true);
        const texCaus = loadTex(causticsUrl, true);
        const texBlue = loadTex(blueUrl, true);
        const texDust = loadTex(dustUrl, true);

        /* ---- live-tunable uniforms (the shader lab writes straight here) ---- */
        const css = getComputedStyle(document.documentElement);
        const num = (name, dflt) => {
            const v = parseFloat(css.getPropertyValue(name));
            return Number.isFinite(v) ? v : dflt;
        };
        const U = {
            flowSpeed: 1.0, fieldGain: 0.62, causticGain: 0.38, glassIOR: 0.6,
            orbRadius: 0.15, orbEnergy: 0.28,
            bloomGain: num('--at-bloom', 0.85), bloomThreshold: 0.62, bloomKnee: 0.28,
            aberration: num('--at-aberration', 0.7), scanline: num('--at-scanline', 0.05),
            grain: num('--at-grain', 0.055), vignette: num('--at-vignette', 0.42),
            curvature: num('--at-curvature', 0.035), dust: 0.35,
            glitch: 0, exposure: 1.0, paused: false
        };
        window.__ATOM_VIS = {
            U, tier: () => quality,
            setTier: (t) => {
                quality = t; setTier(t); calibrating = false;
                try { localStorage.setItem('atom-quality', t); } catch { /* ignore */ }
            },
            unpin: () => { try { localStorage.removeItem('atom-quality'); } catch { /* ignore */ } },
            signatures: STATE_SIGNATURE
        };

        /* ---- spring-driven state cross-fade -------------------------------- */
        let curSig = { ...STATE_SIGNATURE.idle };
        let fromSig = { ...STATE_SIGNATURE.idle };
        let toSig = { ...STATE_SIGNATURE.idle };
        let mix = 1, mixVel = 0, lastState = 'idle';
        let glitchDecay = 0;

        let raf = 0, t0 = performance.now(), last = t0;
        let frames = 0, slow = 0, calibrating = !calibrateOff;

        const render = (now) => {
            raf = requestAnimationFrame(render);
            const dt = Math.min(0.05, (now - last) / 1000); last = now;
            if (U.paused || document.hidden) return;

            const time = (now - t0) / 1000;

            // ---- state transition (critically damped spring on `mix`) -------
            const s = stateRef.current;
            if (s !== lastState) {
                fromSig = { ...curSig };
                toSig = STATE_SIGNATURE[s] || STATE_SIGNATURE.idle;
                mix = 0; mixVel = 0;
                if (s === 'error') glitchDecay = 1;   // sharp, per the motion language
                lastState = s;
            }
            const k = 150, c = 2 * Math.sqrt(k);
            mixVel += (k * (1 - mix) - c * mixVel) * dt;
            mix = Math.min(1, mix + mixVel * dt);
            curSig = {
                col: fromSig.col.map((v, i) => v + (toSig.col[i] - v) * mix),
                turb: fromSig.turb + (toSig.turb - fromSig.turb) * mix,
                energy: fromSig.energy + (toSig.energy - fromSig.energy) * mix,
                speed: fromSig.speed + (toSig.speed - fromSig.speed) * mix
            };
            glitchDecay = Math.max(0, glitchDecay - dt * 1.8);

            // ---- sizing ------------------------------------------------------
            const scale = TIER_SCALE[quality] || 0.6;
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            const cw = Math.max(1, Math.round(canvas.clientWidth * dpr * scale));
            const ch = Math.max(1, Math.round(canvas.clientHeight * dpr * scale));
            if (canvas.width !== cw || canvas.height !== ch) {
                canvas.width = cw; canvas.height = ch;
            }
            sizeTarget(tScene, cw, ch);
            const bw = Math.max(1, cw >> 2), bh = Math.max(1, ch >> 2);
            sizeTarget(tA, bw, bh); sizeTarget(tB, bw, bh);

            gl.bindVertexArray(vao);
            gl.disable(gl.DEPTH_TEST);
            gl.disable(gl.BLEND);

            const live = liveRef.current;
            const bandArr = live.bands && live.bands.length === 4
                ? live.bands
                : [0.35, 0.25, 0.15, 0.1].map(v => v * (0.6 + 0.4 * Math.sin(time * 1.7)));

            // ---- PASS 1: scene ----------------------------------------------
            gl.bindFramebuffer(gl.FRAMEBUFFER, tScene.fb);
            gl.viewport(0, 0, cw, ch);
            gl.useProgram(progScene.p);
            const L = progScene.loc;
            gl.uniform2f(L.uRes, cw, ch);
            gl.uniform1f(L.uTime, time);
            gl.uniform3f(L.uColA, ...fromSig.col);
            gl.uniform3f(L.uColB, ...toSig.col);
            gl.uniform1f(L.uMix, mix);
            gl.uniform1f(L.uTurbA, fromSig.turb);
            gl.uniform1f(L.uTurbB, toSig.turb);
            gl.uniform1f(L.uFlowSpeed, U.flowSpeed * curSig.speed);
            gl.uniform1f(L.uFieldGain, U.fieldGain);
            gl.uniform1f(L.uCausticGain, U.causticGain);
            gl.uniform1f(L.uGlassIOR, U.glassIOR);
            const o = live.orb;
            gl.uniform2f(L.uOrbPos, o ? o.x : 0.5, o ? o.y : 0.62);
            gl.uniform1f(L.uOrbRadius, o && o.r ? o.r : U.orbRadius);
            gl.uniform1f(L.uOrbEnergy, U.orbEnergy + curSig.energy * 0.8);
            gl.uniform1f(L.uAudio, live.audio || 0);
            gl.uniform4f(L.uBands, bandArr[0], bandArr[1], bandArr[2], bandArr[3]);
            gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, texFlow);
            gl.uniform1i(L.uFlow, 0);
            gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, texCaus);
            gl.uniform1i(L.uCaustics, 1);
            gl.drawArrays(gl.TRIANGLES, 0, 3);

            // ---- PASSES 2-4: real bloom, skipped on lower tiers --------------
            const doBloom = TIER_BLOOM[quality] && U.bloomGain > 0.001;
            if (doBloom) {
                gl.bindFramebuffer(gl.FRAMEBUFFER, tA.fb);
                gl.viewport(0, 0, bw, bh);
                gl.useProgram(progThresh.p);
                gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tScene.tx);
                gl.uniform1i(progThresh.loc.uTex, 0);
                gl.uniform1f(progThresh.loc.uThreshold, U.bloomThreshold);
                gl.uniform1f(progThresh.loc.uKnee, U.bloomKnee);
                gl.drawArrays(gl.TRIANGLES, 0, 3);

                gl.useProgram(progBlur.p);
                for (const [src, dst, dx, dy] of [[tA, tB, 1 / bw, 0], [tB, tA, 0, 1 / bh]]) {
                    gl.bindFramebuffer(gl.FRAMEBUFFER, dst.fb);
                    gl.viewport(0, 0, bw, bh);
                    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, src.tx);
                    gl.uniform1i(progBlur.loc.uTex, 0);
                    gl.uniform2f(progBlur.loc.uDir, dx, dy);
                    gl.drawArrays(gl.TRIANGLES, 0, 3);
                }
            }

            // ---- PASS 5: composite ------------------------------------------
            gl.bindFramebuffer(gl.FRAMEBUFFER, null);
            gl.viewport(0, 0, cw, ch);
            gl.useProgram(progComp.p);
            const C = progComp.loc;
            gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tScene.tx);
            gl.uniform1i(C.uScene, 0);
            gl.activeTexture(gl.TEXTURE1); gl.bindTexture(gl.TEXTURE_2D, doBloom ? tA.tx : tScene.tx);
            gl.uniform1i(C.uBloom, 1);
            gl.activeTexture(gl.TEXTURE2); gl.bindTexture(gl.TEXTURE_2D, texBlue);
            gl.uniform1i(C.uBlue, 2);
            gl.activeTexture(gl.TEXTURE3); gl.bindTexture(gl.TEXTURE_2D, texDust);
            gl.uniform1i(C.uDust, 3);
            gl.uniform2f(C.uRes, cw, ch);
            gl.uniform1f(C.uTime, time);
            gl.uniform1f(C.uBloomGain, doBloom ? U.bloomGain : 0);
            gl.uniform1f(C.uAberration, U.aberration);
            gl.uniform1f(C.uScanline, U.scanline);
            gl.uniform1f(C.uGrain, U.grain);
            gl.uniform1f(C.uVignette, U.vignette);
            gl.uniform1f(C.uCurvature, U.curvature);
            gl.uniform1f(C.uDustGain, U.dust);
            gl.uniform1f(C.uGlitch, Math.max(U.glitch, glitchDecay));
            gl.uniform1f(C.uExposure, U.exposure);
            gl.drawArrays(gl.TRIANGLES, 0, 3);

            // ---- auto-downgrade: measure, don't assume ----------------------
            if (calibrating) {
                frames++;
                if (dt > 0.0215) slow++;             // missed a 46fps floor
                if (frames > 120) {
                    if (slow / frames > 0.25) {
                        // The calibrator may soften the look, but it must never
                        // delete it. 'balanced' is the floor: the field, the orb
                        // and the grade all survive, only bloom and resolution
                        // give way. Dropping to 'reduced' tears the canvas down
                        // entirely, and that is reserved for principled reasons
                        // -- no WebGL2, a software renderer, or the user asking
                        // for reduced motion/transparency -- never for a
                        // transient frame dip while the model happens to be
                        // generating.
                        const next = quality === 'ultra' ? 'high'
                            : quality === 'high' ? 'balanced' : 'balanced';
                        if (next !== quality) {
                            console.info(`[ATOM] ${Math.round(slow / frames * 100)}% slow frames — dropping to ${next}`);
                            quality = next; setTier(next);
                        }
                        frames = 0; slow = 0;        // re-measure at the new tier
                    } else {
                        calibrating = false;
                    }
                }
            }
        };
        raf = requestAnimationFrame(render);

        return () => {
            cancelAnimationFrame(raf);
            [tScene, tA, tB].forEach(t => { gl.deleteFramebuffer(t.fb); gl.deleteTexture(t.tx); });
            [texFlow, texCaus, texBlue, texDust].forEach(t => gl.deleteTexture(t));
            [progScene, progThresh, progBlur, progComp].forEach(p => p && gl.deleteProgram(p.p));
            gl.getExtension('WEBGL_lose_context')?.loseContext();
            delete window.__ATOM_VIS;
        };
    }, []);

    // Reduced tier renders no canvas at all — the token layer carries it.
    if (tier === 'reduced') return null;

    return (
        <canvas
            ref={canvasRef}
            aria-hidden="true"
            style={{
                position: 'fixed', inset: 0, width: '100%', height: '100%',
                zIndex: 0, pointerEvents: 'none', display: 'block',
                opacity: 'var(--at-gl-opacity, 1)'
            }}
        />
    );
}

/**
 * Mounted by App.jsx inside WebSocketProvider. Feeds the real voice_status
 * stream into the field, so the background genuinely reflects what ATOM is
 * doing rather than animating on a timer.
 */
export function AtomBackdropLive(props) {
    const ws = useWebSocket();
    const state = ws?.voiceStatus || 'idle';
    return <AtomBackdrop state={state} {...props} />;
}
