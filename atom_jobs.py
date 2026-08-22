"""Idempotency primitives for scheduled ATOM work."""

import sqlite3
from pathlib import Path


class JobLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path)
        try:
            con.execute(
                "CREATE TABLE IF NOT EXISTS runs (job_key TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            con.commit()
        finally:
            con.close()

    def claim(self, job_key: str) -> bool:
        if not job_key.strip() or len(job_key) > 240:
            raise ValueError("invalid job key")
        con = sqlite3.connect(self.path)
        try:
            try:
                con.execute("INSERT INTO runs(job_key) VALUES (?)", (job_key,))
                con.commit()
            except sqlite3.IntegrityError:
                return False
            return True
        finally:
            con.close()
