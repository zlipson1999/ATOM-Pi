/**
 * ATOM-Pi — LIBRARY screen (ATOM-owned component, not an upstream patch)
 *
 * Surfaces the USB knowledge library on the touchscreen. Until now
 * atom_knowledge.py was reachable only as a chat tool or from the CLI,
 * so there was no way to see what is actually on the drive.
 *
 * Talks to the ATOM library router (atom_library_api.py):
 *   GET  /library/status   POST /library/search   POST /library/index
 *
 * Honest by construction: it renders exactly what the backend returned.
 * A missing drive, an empty result, or a failed search each say so in
 * plain language. Nothing is summarised, inferred, or invented here.
 *
 * Follows pocket-ai's own conventions: apiFetch, the pixel-* classes,
 * and useFocusableInput so the on-screen keyboard appears (the Pi's
 * display is a touchscreen with no physical keyboard).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Search, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../apiClient.js';
import { useFocusableInput } from '../contexts/KeyboardContext.jsx';
import LoadingSpinner from './LoadingSpinner';

export default function AtomLibrary() {
    const navigate = useNavigate();
    const { onFocus: onKeyboardFocus, onBlur: onKeyboardBlur } = useFocusableInput(false);

    const [status, setStatus] = useState(null);
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(null);   // null = nothing searched yet
    const [detail, setDetail] = useState(null);
    const [busy, setBusy] = useState(false);
    const [indexing, setIndexing] = useState(false);

    const loadStatus = useCallback(async () => {
        try {
            setStatus(await apiFetch('/library/status'));
        } catch (e) {
            setStatus({ connected: false, detail: `Backend unreachable: ${e.message}` });
        }
    }, []);

    useEffect(() => { loadStatus(); }, [loadStatus]);

    const search = async () => {
        if (!query.trim() || busy) return;
        setBusy(true);
        try {
            const d = await apiFetch('/library/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            setResults(d.results || []);
            setDetail(d.detail || null);
        } catch (e) {
            setResults([]);
            setDetail(`Search failed: ${e.message}`);
        } finally {
            setBusy(false);
        }
    };

    const reindex = async () => {
        if (indexing) return;
        setIndexing(true);
        setDetail('Indexing the drive — this walks every folder and can take a while.');
        try {
            const d = await apiFetch('/library/index', { method: 'POST' });
            setDetail(d.detail || null);
            await loadStatus();
        } catch (e) {
            setDetail(`Indexing failed: ${e.message}`);
        } finally {
            setIndexing(false);
        }
    };

    const connected = status?.connected;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative w-full h-full max-w-full mx-auto overflow-hidden bg-[var(--pixel-bg)] flex flex-col"
        >
            {/* Header — same shape as the other screens */}
            <div className="p-4 z-10 flex justify-between items-center bg-[var(--pixel-surface)] border-b-4 border-[var(--pixel-border)]">
                <button onClick={() => navigate('/')} className="pixel-btn p-3 flex items-center justify-center">
                    <ArrowLeft size={24} />
                </button>
                <h1 className="text-xl font-['Press_Start_2P'] text-[var(--pixel-secondary)]">LIBRARY</h1>
                <div className="w-12" />
            </div>

            {/* Drive status — the first thing worth knowing */}
            <div className="px-4 py-3 flex items-center justify-between gap-3 border-b-2 border-[var(--pixel-border)]">
                <div className="font-['VT323'] text-lg leading-tight min-w-0">
                    {status === null ? (
                        <span className="text-[var(--pixel-border)]">CHECKING DRIVE...</span>
                    ) : connected ? (
                        <span className="text-[var(--pixel-accent)]">
                            DRIVE CONNECTED
                            <span className="text-[var(--pixel-text)]">
                                {' '}&middot; {status.zims} ZIM &middot; {status.documents} DOCS
                            </span>
                        </span>
                    ) : (
                        <span className="text-[#f7768e]">NO DRIVE</span>
                    )}
                </div>
                <button
                    onClick={reindex}
                    disabled={!connected || indexing}
                    className="pixel-btn text-[10px] px-3 py-2 disabled:opacity-40"
                >
                    <RefreshCw size={16} className={indexing ? 'animate-spin' : ''} />
                    {indexing ? 'INDEXING' : 'INDEX'}
                </button>
            </div>

            {/* Search */}
            <div className="p-4 flex gap-2">
                <input
                    className="pixel-input flex-1 min-w-0 text-xl py-3"
                    placeholder="Search the drive..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') search(); }}
                    onFocus={onKeyboardFocus}
                    onBlur={onKeyboardBlur}
                />
                <button onClick={search} disabled={busy || !query.trim()}
                        className="pixel-btn px-4 disabled:opacity-40">
                    <Search size={22} />
                </button>
            </div>

            {/* Results — rendered exactly as returned */}
            <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 scroller-pixel touch-scroll-y">
                {busy ? (
                    <LoadingSpinner label="SEARCHING..." className="h-full" />
                ) : (
                    <>
                        {detail && (
                            <p className="font-['VT323'] text-lg text-[var(--pixel-border)] leading-snug mb-3">
                                {detail}
                            </p>
                        )}
                        {results === null && !detail && (
                            <p className="font-['VT323'] text-lg text-[var(--pixel-border)]">
                                {connected
                                    ? 'Search the books, PDFs and Kiwix content on your drive.'
                                    : 'Plug in the library drive, or set ATOM_LIBRARY_PATH in .env.'}
                            </p>
                        )}
                        <div className="flex flex-col gap-3">
                            {(results || []).map((r, i) => (
                                <div key={i}
                                     className="bg-[var(--pixel-surface)] border-2 border-[var(--pixel-border)] p-3">
                                    <div className="text-[11px] font-['Press_Start_2P'] text-[var(--pixel-secondary)] mb-1 break-words">
                                        {r.title || 'UNTITLED'}
                                    </div>
                                    <div className="font-['VT323'] text-sm text-[var(--pixel-border)] mb-2 break-all">
                                        {r.source}
                                    </div>
                                    <p className="font-['VT323'] text-lg text-[var(--pixel-text)] leading-snug break-words">
                                        {r.text}
                                    </p>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </motion.div>
    );
}
