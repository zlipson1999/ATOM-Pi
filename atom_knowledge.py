"""
ATOM-Pi Local Knowledge (ATOM-owned module — not an upstream patch)
====================================================================
Real retrieval from an external USB drive: Kiwix/ZIM collections and
document libraries (PDF/EPUB/TXT/MD), on drives up to multi-TB.

Design rules honored:
  * Content STAYS on the external drive; only a compact SQLite FTS5
    index (text snippets + paths) lives on the Pi at
    ~/pocket-ai/library_index/ for fast retrieval.
  * Disconnect-safe: every query re-checks the mount; a missing drive
    returns a friendly "library offline" answer, never a crash, and
    reconnecting resumes without re-indexing.
  * No fabrication: answers carry real titles/paths; if retrieval
    found nothing, ATOM says so.
  * Local knowledge stays local: nothing here calls the cloud; the
    only network use is compare_sources(), which ALSO runs the
    existing web tool and says so explicitly.

Kiwix path: uses kiwix-serve (apt: kiwix-tools) started lazily on
localhost:${KIWIX_PORT:-8090} against every *.zim found on the drive,
queried via its search endpoint — actual retrieved content, not an
LLM pretending.

CLI:
  python atom_knowledge.py --status          drive/zim/index summary
  python atom_knowledge.py --index           (re)index documents
  python atom_knowledge.py "search terms"    query the library
"""

import html
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(__file__).parent
INDEX_DIR = Path(os.environ.get("LIBRARY_INDEX_DIR", HOME / "library_index"))
KIWIX_PORT = int(os.environ.get("KIWIX_PORT", "8090"))
LIB_ENV = os.environ.get("ATOM_LIBRARY_PATH", "").strip()
DOC_EXT = {".pdf", ".txt", ".md", ".epub"}
MAX_INDEX_CHARS = 200_000  # per document, keeps multi-TB drives sane
SNIPPET = 700
INDEX_SCHEMA_VERSION = 2


# ---------------------------------------------------------------- discovery
def find_library() -> Path | None:
    """The library root: $ATOM_LIBRARY_PATH if set, else the first
    mounted volume under /media or /mnt containing an 'atom-library'
    folder or any .zim file. Re-run on every query (disconnect-safe)."""
    if LIB_ENV:
        p = Path(LIB_ENV)
        return p if p.exists() else None
    roots = []
    for base in (Path("/media"), Path("/mnt")):
        if base.exists():
            roots += [d for d in base.glob("*/*") if d.is_dir()]
            roots += [d for d in base.glob("*") if d.is_dir()]
    for r in roots:
        if (r / "atom-library").is_dir():
            return r / "atom-library"
    for r in roots:
        try:
            if any(r.rglob("*.zim")):
                return r
        except (PermissionError, OSError):
            continue
    return None


def _zims(root: Path):
    try:
        return sorted(root.rglob("*.zim"))[:50]
    except OSError:
        return []


# ---------------------------------------------------------------- kiwix
def _kiwix_up() -> bool:
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{KIWIX_PORT}/", timeout=1.5)
        return True
    except Exception:
        return False


def _ensure_kiwix(root: Path) -> bool:
    if _kiwix_up():
        return True
    zims = _zims(root)
    if not zims:
        return False
    try:
        # --address 127.0.0.1 is REQUIRED, not cosmetic: kiwix-serve defaults
        # to 0.0.0.0, which publishes the user's entire offline library to
        # every device on the network. This module promises local-only.
        subprocess.Popen(
            ["kiwix-serve", "--address", "127.0.0.1", "--port", str(KIWIX_PORT)]
            + [str(z) for z in zims],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False  # kiwix-tools not installed
    for _ in range(20):
        if _kiwix_up():
            return True
        time.sleep(0.4)
    # Deliberately no retry without --address. kiwix-tools older than 3.0
    # lacks the flag; the answer there is to upgrade, not to bind wide.
    print(
        "[atom_knowledge] kiwix-serve did not come up on 127.0.0.1:"
        f"{KIWIX_PORT}. If your kiwix-tools predates 3.0 it has no "
        "--address flag — upgrade it (sudo apt install kiwix-tools). "
        "ZIM search is off until then; document search still works."
    )
    return False


def _strip_html(s: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def kiwix_search(root: Path, query: str, n: int = 2) -> list[dict]:
    """Search kiwix-serve and fetch the top article bodies. Returns
    [{title, source, text}] — genuinely retrieved content."""
    if not _ensure_kiwix(root):
        return []
    base = f"http://127.0.0.1:{KIWIX_PORT}"
    q = urllib.parse.quote(query)
    try:
        raw = (
            urllib.request.urlopen(f"{base}/search?pattern={q}&pageLength={n}", timeout=8)
            .read()
            .decode(errors="ignore")
        )
    except Exception:
        return []
    links = (
        re.findall(r'href="(/viewer#[^"]+|/content/[^"]+)"[^>]*>([^<]+)<', raw)[:n]
        or re.findall(r'href="([^"]+)"[^>]*>([^<]+)<', raw)[:n]
    )
    out = []
    for href, title in links:
        href = href.replace("/viewer#", "/content/")
        try:
            body = (
                urllib.request.urlopen(base + urllib.parse.quote(href, safe="/:#?=&"), timeout=8)
                .read()
                .decode(errors="ignore")
            )
            text = _strip_html(body)[:SNIPPET]
            if text:
                out.append(
                    {
                        "title": html.unescape(title).strip(),
                        "source": "Kiwix: " + href.split("/content/")[-1][:80],
                        "text": text,
                    }
                )
        except Exception:
            continue
    return out


# ---------------------------------------------------------------- documents
def _db(root: Path) -> sqlite3.Connection:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)  # parents: LIBRARY_INDEX_DIR may be nested
    key = re.sub(r"\W+", "_", str(root))[:60]
    con = sqlite3.connect(INDEX_DIR / f"{key}.db")
    con.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    version = con.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    if version and version[0] != str(INDEX_SCHEMA_VERSION):
        con.execute("DROP TABLE IF EXISTS docs")
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path UNINDEXED, mtime UNINDEXED, size UNINDEXED, title, body)"
    )
    con.execute(
        "INSERT OR REPLACE INTO metadata VALUES ('schema_version', ?)", (str(INDEX_SCHEMA_VERSION),)
    )
    con.commit()
    return con


def _extract(p: Path) -> str:
    try:
        if p.suffix.lower() == ".pdf":
            r = subprocess.run(
                ["pdftotext", "-q", str(p), "-"], capture_output=True, text=True, timeout=60
            )
            return r.stdout[:MAX_INDEX_CHARS]
        if p.suffix.lower() == ".epub":
            import zipfile

            with zipfile.ZipFile(p) as z:
                parts = [
                    z.read(n).decode(errors="ignore")
                    for n in z.namelist()
                    if n.endswith((".xhtml", ".html"))
                ][:30]
            return _strip_html(" ".join(parts))[:MAX_INDEX_CHARS]
        # Read only what we will keep. The previous form read the whole file
        # into memory and then sliced — a single large .txt on a multi-TB
        # drive (the documented use case) could exhaust the Pi's RAM.
        with p.open("r", errors="ignore") as fh:
            return fh.read(MAX_INDEX_CHARS)
    except Exception:
        return ""


def _walk(root: Path):
    """Yield files under root, tolerating permission errors and skipping
    symlinked directories (a symlink loop on a user's drive would otherwise
    make indexing run forever)."""
    stack = [root]
    seen = set()
    while stack:
        d = stack.pop()
        try:
            real = d.resolve()
            if real in seen:
                continue
            seen.add(real)
            entries = list(d.iterdir())
        except (PermissionError, OSError):
            continue
        for e in entries:
            try:
                if e.is_symlink():
                    continue
                if e.is_dir():
                    stack.append(e)
                elif e.is_file():
                    yield e
            except (PermissionError, OSError):
                continue


def index_documents(root: Path) -> str:
    con = _db(root)
    try:
        known = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path, mtime, size FROM docs")}
        seen = set()
        added = updated = 0
        for p in _walk(root):
            if p.suffix.lower() in DOC_EXT:
                path = str(p)
                seen.add(path)
                stat = p.stat()
                fingerprint = (str(stat.st_mtime_ns), str(stat.st_size))
                if known.get(path) == fingerprint:
                    continue
                body = _extract(p)
                if body.strip():
                    if path in known:
                        con.execute("DELETE FROM docs WHERE path = ?", (path,))
                        updated += 1
                    else:
                        added += 1
                    con.execute(
                        "INSERT INTO docs VALUES (?,?,?,?,?)",
                        (path, *fingerprint, p.stem.replace("_", " "), body),
                    )
                    if (added + updated) % 25 == 0:
                        con.commit()
        removed = len(set(known) - seen)
        for path in set(known) - seen:
            con.execute("DELETE FROM docs WHERE path = ?", (path,))
        con.commit()
        total = con.execute("SELECT count(*) FROM docs").fetchone()[0]
        return f"Indexed {added} new, updated {updated}, removed {removed}; {total} total."
    finally:
        con.close()


def doc_search(root: Path, query: str, n: int = 3) -> list[dict]:
    con = _db(root)
    safe = " ".join(re.findall(r"\w+", query)) or query
    try:
        rows = con.execute(
            "SELECT path, title, snippet(docs, 4, '', '', ' … ', 24) "
            "FROM docs WHERE docs MATCH ? LIMIT ?",
            (safe, n),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()  # one connection per query was leaked before; the
        # backend is long-running and eventually hit the fd cap
    out = []
    for path, title, snip in rows:
        exists = Path(path).exists()
        out.append(
            {
                "title": title,
                "source": path if exists else path + " (drive disconnected)",
                "text": snip,
            }
        )
    return out


# ---------------------------------------------------------------- tools
def search_library(query: str = "") -> str:
    """Tool: answer from the local USB library (Kiwix + documents)."""
    query = (query or "").strip()
    if not query:
        return "What should I look up in the library?"
    root = find_library()
    if root is None:
        return "My local library drive isn't connected right now. Plug it in and ask me again."
    hits = kiwix_search(root, query) + doc_search(root, query)
    if not hits:
        return (
            f"I searched the local library and didn't find anything "
            f"about '{query}'. The drive is connected — it may just "
            f"not cover that topic, or documents may need indexing "
            f"(run: python atom_knowledge.py --index)."
        )
    parts = [f"From {h['title']} ({h['source']}): {h['text']}" for h in hits[:3]]
    return "Here's what the local library actually says. " + " || ".join(parts)


def compare_sources(query: str = "") -> str:
    """Tool: real local retrieval AND real web search, labeled."""
    local = search_library(query)
    try:
        from tool_ai import run_web_search

        web = run_web_search({"query": query})
    except Exception as exc:
        web = f"Web search unavailable: {exc}"
    return (
        f"LOCAL LIBRARY: {local} \n\nONLINE: {web} \n\n"
        f"Those are the two actual sources; nothing was invented."
    )


# ---------------------------------------------------------------- cli
def status() -> str:
    root = find_library()
    if root is None:
        return "LIBRARY: not connected (set ATOM_LIBRARY_PATH or plug in a drive with an atom-library folder or .zim files)"
    z = len(_zims(root))
    try:
        con = _db(root)
        try:
            n = con.execute("SELECT count(*) FROM docs").fetchone()[0]
        finally:
            con.close()
    except Exception:
        n = 0
    return f"LIBRARY: {root} | {z} ZIM file(s) | {n} indexed document(s)"


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--status":
        print(status())
    elif a[0] == "--index":
        r = find_library()
        print(index_documents(r) if r else "No library drive found.")
    else:
        print(search_library(" ".join(a)))

