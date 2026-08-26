"""
ATOM-Pi Local Knowledge (ATOM-owned module — not an upstream patch)
====================================================================
Real retrieval from a local library: Kiwix/ZIM collections and document
libraries (PDF/EPUB/TXT/MD), on volumes up to multi-TB. The library may
live on the Pi's own NVMe drive (~/atom-library) or on a plugged-in USB
drive -- both are found automatically, removable taking precedence.

Design rules honored:
  * Content STAYS where it is -- nothing is copied. Only a compact
    SQLite FTS5 index (text snippets + paths) lives at
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
DOC_EXT = {".pdf", ".txt", ".md", ".epub"}
MAX_INDEX_CHARS = 200_000          # per document, keeps multi-TB drives sane
SNIPPET = 700


# ---------------------------------------------------------------- discovery
def _scan(root: Path, match, limit: int, max_depth: int) -> list[Path]:
    """Breadth-limited, symlink-safe search under root.

    Path.rglob() is unbounded and follows directory symlinks, so on the
    multi-TB drives this module is built for it could walk for minutes — or
    forever, around a symlink loop — and find_library() runs on EVERY query.
    This walks with an explicit depth cap, skips symlinks, tolerates
    permission errors, and stops as soon as it has `limit` matches.
    """
    out, stack, seen = [], [(root, 0)], set()
    while stack and len(out) < limit:
        d, depth = stack.pop()
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
                    if depth < max_depth:
                        stack.append((e, depth + 1))
                elif match(e):
                    out.append(e)
                    if len(out) >= limit:
                        break
            except (PermissionError, OSError):
                continue
    return out


_LIB_CACHE: Path | None = None
_LIB_SOURCE: str = "none"      # "configured" | "usb" | "internal" | "none"


def removable_roots() -> list[Path]:
    """Mounted volumes that could hold a library. Both /media/<user>/<label>
    and /media/<label> are covered, which is the difference between a desktop
    automount and a hand-written fstab entry."""
    roots = []
    for base in (Path("/media"), Path("/mnt")):
        if base.exists():
            roots += [d for d in base.glob("*/*") if d.is_dir()]
            roots += [d for d in base.glob("*") if d.is_dir()]
    return roots


def internal_candidates() -> list[Path]:
    """Fixed on-board locations to check for a library.

    The Pi now boots from an NVMe drive with room to spare, so requiring a
    USB stick to hold the library is an unnecessary constraint. These are
    checked in order; the first that exists and has content wins.
    """
    return [
        Path.home() / "atom-library",        # ~/atom-library  (the obvious one)
        HOME / "atom-library",               # beside the app: ~/pocket-ai/atom-library
        Path("/srv/atom-library"),           # the FHS answer for served data
        Path("/opt/atom-library"),
    ]


def _has_content(p: Path) -> bool:
    """True if a directory looks like a library rather than an empty folder."""
    if not p.is_dir():
        return False
    if _scan(p, lambda e: e.suffix.lower() == ".zim", limit=1, max_depth=3):
        return True
    return bool(_scan(p, lambda e: e.suffix.lower() in DOC_EXT, limit=1, max_depth=3))


def library_source() -> str:
    """Where the current library came from. Set by find_library()."""
    return _LIB_SOURCE


def find_library() -> Path | None:
    """The library root, searched in this order:

      1. $ATOM_LIBRARY_PATH             — an explicit setting always wins
      2. removable media                — /media or /mnt, a drive you plugged in
      3. internal storage               — ~/atom-library and friends, on the NVMe

    Removable is checked before internal on purpose: plugging a drive in is a
    deliberate act, and it should take precedence over whatever is sitting on
    the boot disk. With no drive attached, the internal library is used, so a
    USB stick is no longer required at all.

    Disconnect-safe: the discovered root is remembered but re-validated on
    every call, so unplugging the drive is noticed immediately and replugging
    resumes without a fresh scan. Only a genuinely absent library pays for a
    search, and that search is depth-bounded.
    """
    global _LIB_CACHE, _LIB_SOURCE
    # Read the environment live rather than at import: start-atom.sh sources
    # .env before launching, but atom_doctor and the CLI import this module
    # directly, where a value set afterwards used to be ignored.
    env = os.environ.get("ATOM_LIBRARY_PATH", "").strip()
    if env:
        p = Path(env)
        if p.exists():
            _LIB_CACHE, _LIB_SOURCE = p, "configured"
            return p
        _LIB_SOURCE = "none"
        return None
    if _LIB_CACHE is not None and _LIB_CACHE.exists():
        return _LIB_CACHE
    _LIB_CACHE, _LIB_SOURCE = None, "none"

    # --- 2. removable media ---------------------------------------------
    for r in removable_roots():
        if (r / "atom-library").is_dir():
            _LIB_CACHE, _LIB_SOURCE = r / "atom-library", "usb"
            return _LIB_CACHE
    for r in removable_roots():
        # Shallow: a .zim buried more than a few levels down on a big drive is
        # not worth stalling every voice query over. Point ATOM_LIBRARY_PATH
        # at it instead.
        if _scan(r, lambda e: e.suffix.lower() == ".zim", limit=1, max_depth=3):
            _LIB_CACHE, _LIB_SOURCE = r, "usb"
            return _LIB_CACHE

    # --- 3. internal storage --------------------------------------------
    # Content-checked rather than existence-checked: an empty ~/atom-library
    # left behind by a tidy-up should not shadow a drive the user plugs in
    # later, nor report a connected library with nothing in it.
    for p in internal_candidates():
        try:
            if _has_content(p):
                _LIB_CACHE, _LIB_SOURCE = p, "internal"
                return p
        except (PermissionError, OSError):
            continue
    return None


def _zims(root: Path):
    return sorted(_scan(root, lambda e: e.suffix.lower() == ".zim",
                        limit=50, max_depth=6))


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
        subprocess.Popen(["kiwix-serve", "--address", "127.0.0.1",
                          "--port", str(KIWIX_PORT)]
                         + [str(z) for z in zims],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        return False  # kiwix-tools not installed
    for _ in range(20):
        if _kiwix_up():
            return True
        time.sleep(0.4)
    # Deliberately no retry without --address. kiwix-tools older than 3.0
    # lacks the flag; the answer there is to upgrade, not to bind wide.
    print("[atom_knowledge] kiwix-serve did not come up on 127.0.0.1:"
          f"{KIWIX_PORT}. If your kiwix-tools predates 3.0 it has no "
          "--address flag — upgrade it (sudo apt install kiwix-tools). "
          "ZIM search is off until then; document search still works.")
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
        raw = urllib.request.urlopen(
            f"{base}/search?pattern={q}&pageLength={n}", timeout=8
        ).read().decode(errors="ignore")
    except Exception:
        return []
    links = re.findall(r'href="(/viewer#[^"]+|/content/[^"]+)"[^>]*>([^<]+)<',
                       raw)[:n] or re.findall(r'href="([^"]+)"[^>]*>([^<]+)<',
                                              raw)[:n]
    out = []
    for href, title in links:
        href = href.replace("/viewer#", "/content/")
        try:
            body = urllib.request.urlopen(base + urllib.parse.quote(href, safe="/:#?=&"),
                                          timeout=8).read().decode(errors="ignore")
            text = _strip_html(body)[:SNIPPET]
            if text:
                out.append({"title": html.unescape(title).strip(),
                            "source": "Kiwix: " + href.split("/content/")[-1][:80],
                            "text": text})
        except Exception:
            continue
    return out


# ---------------------------------------------------------------- documents
def _db(root: Path) -> sqlite3.Connection:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)   # parents: LIBRARY_INDEX_DIR may be nested
    key = re.sub(r"\W+", "_", str(root))[:60]
    con = sqlite3.connect(INDEX_DIR / f"{key}.db")
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5"
                "(path, title, body)")
    # Companion table: FTS5 cannot carry a typed mtime/size usefully, and
    # without them the index could only ever grow — a file edited on the
    # drive kept serving its old text, and a deleted file was never removed.
    con.execute("CREATE TABLE IF NOT EXISTS docmeta"
                "(path TEXT PRIMARY KEY, mtime REAL, size INTEGER)")
    return con


def _extract(p: Path) -> str:
    try:
        if p.suffix.lower() == ".pdf":
            r = subprocess.run(["pdftotext", "-q", str(p), "-"],
                               capture_output=True, text=True, timeout=60)
            return r.stdout[:MAX_INDEX_CHARS]
        if p.suffix.lower() == ".epub":
            import zipfile
            with zipfile.ZipFile(p) as z:
                parts = [z.read(n).decode(errors="ignore")
                         for n in z.namelist() if n.endswith((".xhtml", ".html"))][:30]
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
    """Bring the index in line with what is actually on the drive.

    Adds new documents, re-reads ones whose mtime or size changed, and drops
    ones that no longer exist. Previously this only ever inserted unseen
    paths, so an edited file kept answering with its old text and a deleted
    file stayed searchable forever.
    """
    con = _db(root)
    try:
        known = {r[0]: (r[1], r[2])
                 for r in con.execute("SELECT path, mtime, size FROM docmeta")}
        # Migration: an index built before docmeta existed has rows in `docs`
        # but no stamps. Every file would then look new and be inserted a
        # second time, duplicating every search hit. Rebuild once instead.
        if not known and con.execute("SELECT count(*) FROM docs").fetchone()[0]:
            con.execute("DELETE FROM docs")
            con.commit()
        added = updated = 0
        seen = set()
        for p in _walk(root):
            if p.suffix.lower() not in DOC_EXT:
                continue
            key = str(p)
            seen.add(key)
            try:
                st = p.stat()
                stamp = (st.st_mtime, st.st_size)
            except OSError:
                continue
            prev = known.get(key)
            if prev is not None and prev[0] == stamp[0] and prev[1] == stamp[1]:
                continue                      # unchanged since last index
            body = _extract(p)
            if not body.strip():
                continue
            if prev is not None:
                con.execute("DELETE FROM docs WHERE path = ?", (key,))
                updated += 1
            else:
                added += 1
            con.execute("INSERT INTO docs VALUES (?,?,?)",
                        (key, p.stem.replace("_", " "), body))
            con.execute("INSERT OR REPLACE INTO docmeta VALUES (?,?,?)",
                        (key, stamp[0], stamp[1]))
            if (added + updated) % 25 == 0:
                con.commit()
        # Prune anything indexed earlier that is no longer on the drive. Only
        # safe because _walk just completed a full pass of a mounted root.
        removed = 0
        for gone in set(known) - seen:
            con.execute("DELETE FROM docs WHERE path = ?", (gone,))
            con.execute("DELETE FROM docmeta WHERE path = ?", (gone,))
            removed += 1
        con.commit()
        total = con.execute("SELECT count(*) FROM docs").fetchone()[0]
        return (f"Indexed {added} new, {updated} changed, {removed} removed; "
                f"{total} total in the library index.")
    finally:
        con.close()


def doc_search(root: Path, query: str, n: int = 3) -> list[dict]:
    con = _db(root)
    safe = " ".join(re.findall(r"\w+", query)) or query
    try:
        rows = con.execute(
            "SELECT path, title, snippet(docs, 2, '', '', ' … ', 24) "
            "FROM docs WHERE docs MATCH ? LIMIT ?", (safe, n)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()   # one connection per query was leaked before; the
                      # backend is long-running and eventually hit the fd cap
    out = []
    root_here = root.exists()
    for path, title, snip in rows:
        if Path(path).exists():
            source = path
        elif not root_here:
            source = path + " (drive disconnected)"
        else:
            # The drive is mounted but this file is not on it any more —
            # calling that "disconnected" sent people hunting for a cable.
            source = path + " (file no longer on the drive — re-run --index)"
        out.append({"title": title, "source": source, "text": snip})
    return out


# ---------------------------------------------------------------- tools
def search_library(query: str = "") -> str:
    """Tool: answer from the local USB library (Kiwix + documents)."""
    query = (query or "").strip()
    if not query:
        return "What should I look up in the library?"
    root = find_library()
    if root is None:
        return ("My local library drive isn't connected right now. "
                "Plug it in and ask me again.")
    hits = kiwix_search(root, query) + doc_search(root, query)
    if not hits:
        return (f"I searched the local library and didn't find anything "
                f"about '{query}'. The drive is connected — it may just "
                f"not cover that topic, or documents may need indexing "
                f"(run: python atom_knowledge.py --index).")
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
    return (f"LOCAL LIBRARY: {local} \n\nONLINE: {web} \n\n"
            f"Those are the two actual sources; nothing was invented.")


# ---------------------------------------------------------------- cli
def status() -> str:
    root = find_library()
    if root is None:
        return ("LIBRARY: not found (put it in ~/atom-library on the internal "
                "drive, plug in a drive with an atom-library folder or .zim "
                "files, or set ATOM_LIBRARY_PATH)")
    z = len(_zims(root))
    try:
        con = _db(root)
        try:
            n = con.execute("SELECT count(*) FROM docs").fetchone()[0]
        finally:
            con.close()
    except Exception:
        n = 0
    where = {"configured": "configured", "usb": "removable",
             "internal": "internal"}.get(library_source(), "")
    return (f"LIBRARY: {root} | {where} | {z} ZIM file(s) | "
            f"{n} indexed document(s)")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "--status":
        print(status())
    elif a[0] == "--index":
        r = find_library()
        print(index_documents(r) if r else "No library drive found.")
    else:
        print(search_library(" ".join(a)))
