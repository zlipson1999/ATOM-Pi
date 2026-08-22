"""
ATOM-Pi Library API (ATOM-owned module — not an upstream patch)
===============================================================
Puts the USB knowledge library behind HTTP so the touchscreen can use it.
Until now atom_knowledge.py was reachable only as a chat tool or from the
CLI, so there was no way to browse the drive from the robot itself.

Exposed as a FastAPI APIRouter rather than endpoints edited into app.py:
apply_patches.py then only has to add an import and one include_router()
line, which is a far smaller anchor to keep working against upstream.

    GET  /library/status   drive + index summary
    POST /library/search   {"query": "..."} -> real retrieved passages
    POST /library/index    (re)index documents on the drive

Every handler degrades instead of raising: a missing drive, a missing
kiwix-tools, or an unreadable index returns a normal response with
connected=false and a plain-language reason. Nothing here invents an answer.
"""
import logging

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

import atom_knowledge as ak

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/library", tags=["library"])


class Query(BaseModel):
    query: str = ""


def _root_info():
    root = ak.find_library()
    return root, (str(root) if root else None)


@router.get("/status")
async def library_status():
    """Drive presence, ZIM count and indexed-document count."""
    def work():
        root, path = _root_info()
        if root is None:
            return {"connected": False, "path": None, "zims": 0, "documents": 0,
                    "detail": "No library drive found. Plug in the drive, or set "
                              "ATOM_LIBRARY_PATH in .env."}
        zims = len(ak._zims(root))
        docs = 0
        try:
            con = ak._db(root)
            try:
                docs = con.execute("SELECT count(*) FROM docs").fetchone()[0]
            finally:
                con.close()
        except Exception as exc:
            logger.warning("library index unreadable: %s", exc)
        return {"connected": True, "path": path, "zims": zims, "documents": docs,
                "detail": None}
    return await run_in_threadpool(work)


@router.post("/search")
async def library_search(q: Query):
    """Real retrieval from Kiwix + the document index. Never fabricates."""
    query = (q.query or "").strip()
    if not query:
        return {"query": "", "connected": True, "results": [],
                "detail": "Type something to look up."}

    def work():
        root, path = _root_info()
        if root is None:
            return {"query": query, "connected": False, "results": [],
                    "detail": "The library drive isn't connected."}
        try:
            hits = ak.kiwix_search(root, query) + ak.doc_search(root, query)
        except Exception as exc:
            logger.warning("library search failed: %s", exc)
            return {"query": query, "connected": True, "results": [],
                    "detail": f"Search failed: {exc}"}
        return {
            "query": query, "connected": True, "path": path,
            "results": [{"title": h.get("title", ""),
                         "source": h.get("source", ""),
                         "text": h.get("text", "")} for h in hits],
            "detail": None if hits else
                      "Nothing in the library matched that. The drive is "
                      "connected — it may not cover the topic, or documents "
                      "may need indexing.",
        }
    return await run_in_threadpool(work)


@router.post("/index")
async def library_index():
    """(Re)index documents. Walks the whole drive, so it can take a while."""
    def work():
        root, _ = _root_info()
        if root is None:
            return {"connected": False, "detail": "No library drive found."}
        try:
            return {"connected": True, "detail": ak.index_documents(root)}
        except Exception as exc:
            logger.warning("library index failed: %s", exc)
            return {"connected": True, "detail": f"Indexing failed: {exc}"}
    return await run_in_threadpool(work)
