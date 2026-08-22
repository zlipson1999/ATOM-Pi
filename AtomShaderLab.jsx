/**
 * ATOM — /dev/shader-lab
 * Every uniform in the GL chain as a live slider. Writes straight into the
 * running engine's uniform object, so tuning is instant with no rebuild.
 * Copy Tokens emits the CSS block to paste back into atom-visual.css, which is
 * how a session of tuning becomes a permanent design decision.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { STATE_SIGNATURE } from './AtomBackdrop';

const CONTROLS = [
    ['field', [
        ['flowSpeed', 0, 4, 0.01], ['fieldGain', 0, 2.5, 0.01],
        ['causticGain', 0, 2, 0.01], ['glassIOR', 0, 3, 0.01]]],
    ['orb', [
        ['orbRadius', 0.02, 0.5, 0.005], ['orbEnergy', 0, 2, 0.01]]],
    ['bloom', [
        ['bloomGain', 0, 3, 0.01], ['bloomThreshold', 0, 1.5, 0.01],
        ['bloomKnee', 0.01, 1, 0.01]]],
    ['crt', [
        ['aberration', 0, 4, 0.01], ['scanline', 0, 0.3, 0.002],
        ['grain', 0, 0.3, 0.002], ['vignette', 0, 1.2, 0.01],
        ['curvature', 0, 0.25, 0.002], ['dust', 0, 1.5, 0.01],
        ['glitch', 0, 1, 0.01], ['exposure', 0.2, 2.5, 0.01]]]
];
const TIERS = ['ultra', 'high', 'balanced', 'reduced'];

export default function AtomShaderLab() {
    const navigate = useNavigate();
    const [, force] = useState(0);
    const [fps, setFps] = useState(0);
    const [tier, setTier] = useState('—');
    const vis = () => (typeof window !== 'undefined' ? window.__ATOM_VIS : null);
    const frames = useRef({ n: 0, t: performance.now() });

    useEffect(() => {
        let raf;
        const tick = () => {
            raf = requestAnimationFrame(tick);
            const f = frames.current; f.n++;
            const now = performance.now();
            if (now - f.t >= 500) {
                setFps(Math.round((f.n * 1000) / (now - f.t)));
                f.n = 0; f.t = now;
                const v = vis(); if (v) setTier(v.tier());
            }
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, []);

    const v = vis();
    const set = (k, val) => { if (v) { v.U[k] = val; force(n => n + 1); } };

    const copyTokens = () => {
        if (!v) return;
        const css = `:root {
  --at-bloom: ${v.U.bloomGain};
  --at-aberration: ${v.U.aberration};
  --at-scanline: ${v.U.scanline};
  --at-grain: ${v.U.grain};
  --at-vignette: ${v.U.vignette};
  --at-curvature: ${v.U.curvature};
}`;
        navigator.clipboard?.writeText(css);
    };

    return (
        <div className="w-full h-full overflow-y-auto p-4 flex flex-col gap-4"
             style={{ position: 'relative', zIndex: 1 }}>
            <div className="flex items-center justify-between gap-3">
                <button onClick={() => navigate('/')} className="pixel-btn p-3">
                    <ArrowLeft size={20} />
                </button>
                <h1 className="at-emissive-accent" style={{
                    fontFamily: 'var(--at-font-display)', fontSize: 18,
                    letterSpacing: 'var(--at-tracking-wide)' }}>SHADER LAB</h1>
                <div className="at-data" style={{ fontSize: 12, color: 'var(--at-text-mid)' }}>
                    {fps} fps
                </div>
            </div>

            {!v && (
                <div className="at-glass p-4">
                    <p style={{ color: 'var(--at-text-mid)', fontFamily: 'var(--at-font-ui)' }}>
                        The GL layer is not running — quality tier is
                        <b style={{ color: 'var(--at-text-hi)' }}> reduced</b>. That happens when
                        WebGL2 is unavailable, the GPU is software-rendered, reduced-motion or
                        reduced-transparency is set, or the engine measured too many slow frames.
                        The token layer is still fully in effect.
                    </p>
                </div>
            )}

            {v && (
                <>
                    <div className="at-glass p-3 flex flex-wrap items-center gap-2">
                        <span className="at-label">tier</span>
                        {TIERS.map(t => (
                            <button key={t} onClick={() => v.setTier(t)}
                                className="pixel-btn"
                                style={{ padding: '6px 10px', fontSize: 11,
                                    borderColor: tier === t ? 'var(--at-accent-6)' : undefined,
                                    color: tier === t ? 'var(--at-accent-8)' : undefined }}>
                                {t}
                            </button>
                        ))}
                        <button onClick={() => { v.U.paused = !v.U.paused; force(n => n + 1); }}
                            className="pixel-btn" style={{ padding: '6px 10px', fontSize: 11 }}>
                            {v.U.paused ? 'resume' : 'pause'}
                        </button>
                        <button onClick={copyTokens} className="pixel-btn"
                            style={{ padding: '6px 10px', fontSize: 11 }}>copy tokens</button>
                    </div>

                    {CONTROLS.map(([group, rows]) => (
                        <div key={group} className="at-glass p-3 flex flex-col gap-2">
                            <span className="at-label">{group}</span>
                            {rows.map(([k, min, max, step]) => (
                                <label key={k} className="flex items-center gap-3">
                                    <span className="at-data" style={{
                                        fontSize: 11, width: 116, color: 'var(--at-text-mid)' }}>{k}</span>
                                    <input type="range" min={min} max={max} step={step}
                                        value={v.U[k]} style={{ flex: 1, accentColor: 'var(--at-accent-6)' }}
                                        onChange={e => set(k, parseFloat(e.target.value))} />
                                    <span className="at-data" style={{
                                        fontSize: 11, width: 52, textAlign: 'right',
                                        color: 'var(--at-accent-8)' }}>
                                        {Number(v.U[k]).toFixed(3)}
                                    </span>
                                </label>
                            ))}
                        </div>
                    ))}

                    <div className="at-glass p-3">
                        <span className="at-label">state signatures</span>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))', gap: 8, marginTop: 8 }}>
                            {Object.entries(STATE_SIGNATURE).map(([name, sig]) => (
                                <div key={name} className="at-data" style={{ fontSize: 10, color: 'var(--at-text-lo)' }}>
                                    <span style={{
                                        display: 'inline-block', width: 10, height: 10, marginRight: 6,
                                        borderRadius: 2, verticalAlign: 'middle',
                                        background: `rgb(${sig.col.map(c => Math.round(c * 255)).join(',')})`,
                                        boxShadow: `0 0 10px rgb(${sig.col.map(c => Math.round(c * 255)).join(',')})`
                                    }} />
                                    {name}
                                </div>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
