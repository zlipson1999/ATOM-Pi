/**
 * ATOM — procedural texture generator
 * ---------------------------------------------------------------------------
 * Bakes every texture the visual system needs. No stock assets, no runtime
 * dependencies, no network: run `node tools/gen_textures.mjs` and the files in
 * atom-textures/ are reproduced bit-for-bit from the seeds below.
 *
 * Why bake at all when the shaders could compute this live? Fill rate. The Pi
 * 5's VideoCore VII is doing this work per-pixel per-frame while a 4B model is
 * generating tokens. Four octaves of fbm sampled from a texture costs one
 * fetch; computed inline it costs ~24 hash operations. Baking is the single
 * biggest saving available in the whole chain.
 *
 * Everything here is TILEABLE — sampled with GL_REPEAT and scrolled, so a
 * 256px texture covers an arbitrarily large moving field with no visible seam.
 */
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const OUT = join(dirname(fileURLToPath(import.meta.url)), '..', 'atom-textures');
mkdirSync(OUT, { recursive: true });

/* ---------- minimal PNG encoder (RGBA8, no filtering) --------------------- */
const CRC = (() => {
    const t = new Int32Array(256);
    for (let n = 0; n < 256; n++) {
        let c = n;
        for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
        t[n] = c;
    }
    return t;
})();
function crc32(buf) {
    let c = ~0;
    for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
    return ~c >>> 0;
}
function chunk(type, data) {
    const len = Buffer.alloc(4); len.writeUInt32BE(data.length);
    const td = Buffer.concat([Buffer.from(type, 'ascii'), data]);
    const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td));
    return Buffer.concat([len, td, crc]);
}
function writePNG(path, w, h, rgba) {
    const raw = Buffer.alloc((w * 4 + 1) * h);
    for (let y = 0; y < h; y++) {
        raw[y * (w * 4 + 1)] = 0;                       // filter: none
        rgba.copy(raw, y * (w * 4 + 1) + 1, y * w * 4, (y + 1) * w * 4);
    }
    const ihdr = Buffer.alloc(13);
    ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
    ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    writeFileSync(path, Buffer.concat([
        Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
        chunk('IHDR', ihdr),
        chunk('IDAT', deflateSync(raw, { level: 9 })),
        chunk('IEND', Buffer.alloc(0))
    ]));
    console.log(`  ${path.split('/').pop().padEnd(22)} ${w}x${h}`);
}

/* ---------- deterministic hash + tileable value noise --------------------- */
const seedHash = (x, y, s) => {
    let h = (x * 374761393 + y * 668265263 + s * 2246822519) | 0;
    h = (h ^ (h >>> 13)) * 1274126177;
    return ((h ^ (h >>> 16)) >>> 0) / 4294967295;
};
const smooth = (t) => t * t * (3 - 2 * t);

/** Value noise on a period-P lattice, so it wraps exactly. */
function tileNoise(x, y, P, s) {
    const xi = Math.floor(x), yi = Math.floor(y);
    const xf = x - xi, yf = y - yi;
    const w = (a) => ((a % P) + P) % P;
    const n = (a, b) => seedHash(w(a), w(b), s);
    const u = smooth(xf), v = smooth(yf);
    return (n(xi, yi) * (1 - u) + n(xi + 1, yi) * u) * (1 - v)
         + (n(xi, yi + 1) * (1 - u) + n(xi + 1, yi + 1) * u) * v;
}
/** Fractal Brownian motion — octaves double frequency, halve amplitude. */
function fbm(x, y, P, oct, s) {
    let sum = 0, amp = 0.5, freq = 1, norm = 0;
    for (let i = 0; i < oct; i++) {
        sum += amp * tileNoise(x * freq, y * freq, P * freq, s + i * 17);
        norm += amp; amp *= 0.5; freq *= 2;
    }
    return sum / norm;
}

/* ---------- 1. flow field: 4 fbm scales packed one per channel ------------ */
{
    const N = 256, P = 8, px = Buffer.alloc(N * N * 4);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const u = (x / N) * P, v = (y / N) * P, i = (y * N + x) * 4;
        px[i]     = fbm(u,       v,       P, 5, 1) * 255;   // R coarse structure
        px[i + 1] = fbm(u * 2,   v * 2,   P * 2, 4, 2) * 255; // G mid detail
        px[i + 2] = fbm(u * 4,   v * 4,   P * 4, 3, 3) * 255; // B fine detail
        px[i + 3] = fbm(u * 0.5, v * 0.5, Math.max(1, P / 2), 3, 4) * 255; // A drift
    }
    writePNG(join(OUT, 'atom-flow.png'), N, N, px);
}

/* ---------- 2. caustics: interfering sine lobes, light through water ------ */
{
    const N = 256, px = Buffer.alloc(N * N * 4);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        const u = (x / N) * Math.PI * 2, v = (y / N) * Math.PI * 2;
        let c = 0;
        // Each lobe uses integer frequencies so the pattern wraps cleanly.
        for (const [fx, fy, ph] of [[1,2,0],[2,1,1.7],[3,2,3.1],[2,3,4.4],[4,1,2.2]]) {
            c += Math.sin(u * fx + Math.cos(v * fy + ph) * 1.8 + ph);
        }
        c = Math.pow(Math.max(0, c / 5) * 0.5 + 0.5, 3.2);   // sharpen the ridges
        const g = Math.min(255, c * 255) | 0, i = (y * N + x) * 4;
        px[i] = px[i + 1] = px[i + 2] = g; px[i + 3] = 255;
    }
    writePNG(join(OUT, 'atom-caustics.png'), N, N, px);
}

/* ---------- 3. blue-ish noise for dithering ------------------------------- */
/* Void-and-cluster is overkill here; a high-pass over white noise gives a
   spectrum flat enough to kill 8-bit gradient banding without visible clumps. */
{
    const N = 64, white = new Float64Array(N * N);
    for (let i = 0; i < N * N; i++) white[i] = seedHash(i % N, (i / N) | 0, 99);
    const lp = new Float64Array(N * N);
    for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
        let s = 0, n = 0;
        for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
            s += white[(((y + dy + N) % N) * N) + ((x + dx + N) % N)]; n++;
        }
        lp[y * N + x] = s / n;
    }
    const hp = new Float64Array(N * N);
    for (let i = 0; i < N * N; i++) hp[i] = white[i] - lp[i] + 0.5;
    const sorted = [...hp].sort((a, b) => a - b);   // histogram-flatten to 0..1
    const rank = new Map(sorted.map((v, i) => [v, i / (sorted.length - 1)]));
    const px = Buffer.alloc(N * N * 4);
    for (let i = 0; i < N * N; i++) {
        const g = (rank.get(hp[i]) * 255) | 0;
        px[i * 4] = px[i * 4 + 1] = px[i * 4 + 2] = g; px[i * 4 + 3] = 255;
    }
    writePNG(join(OUT, 'atom-bluenoise.png'), N, N, px);
}

/* ---------- 4. dust and scratches: the CRT is not a clean surface --------- */
{
    const N = 256, px = Buffer.alloc(N * N * 4, 0);
    for (let i = 3; i < px.length; i += 4) px[i] = 255;
    // dust motes
    for (let k = 0; k < 900; k++) {
        const x = (seedHash(k, 7, 51) * N) | 0, y = (seedHash(k, 13, 52) * N) | 0;
        const b = 40 + seedHash(k, 3, 53) * 140, i = (y * N + x) * 4;
        px[i] = px[i + 1] = px[i + 2] = b | 0;
    }
    // hairline scratches, wrapped
    for (let k = 0; k < 22; k++) {
        let x = seedHash(k, 21, 61) * N, y = seedHash(k, 22, 62) * N;
        const a = seedHash(k, 23, 63) * Math.PI * 2;
        const len = 20 + seedHash(k, 24, 64) * 90;
        for (let t = 0; t < len; t++) {
            const xi = (Math.round(x + Math.cos(a) * t) % N + N) % N;
            const yi = (Math.round(y + Math.sin(a) * t) % N + N) % N;
            const i = (yi * N + xi) * 4, b = 90 + seedHash(k, t, 65) * 90;
            px[i] = px[i + 1] = px[i + 2] = Math.max(px[i], b | 0);
        }
    }
    writePNG(join(OUT, 'atom-dust.png'), N, N, px);
}

console.log('atom-textures/ regenerated deterministically.');
