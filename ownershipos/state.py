from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class DecisionStore:
    def __init__(self, path: str = "ownershipos.db"):
        self.path = Path(path)
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS decisions (
                fingerprint TEXT PRIMARY KEY, decision TEXT NOT NULL,
                proposal_json TEXT NOT NULL, decided_at TEXT DEFAULT CURRENT_TIMESTAMP,
                applied_at TEXT, api_result TEXT)""")

    def _connect(self):
        return sqlite3.connect(self.path)

    def decided(self, fingerprint: str) -> bool:
        with self._connect() as con:
            return con.execute("SELECT 1 FROM decisions WHERE fingerprint=?", (fingerprint,)).fetchone() is not None

    def save(self, proposal: dict, decision: str):
        with self._connect() as con:
            con.execute("INSERT OR REPLACE INTO decisions(fingerprint,decision,proposal_json) VALUES(?,?,?)",
                        (proposal["fingerprint"], decision, json.dumps(proposal, sort_keys=True)))

    def pending_approvals(self) -> list[dict]:
        with self._connect() as con:
            rows = con.execute("SELECT proposal_json FROM decisions WHERE decision='Approved' AND applied_at IS NULL").fetchall()
        return [json.loads(row[0]) for row in rows]

    def mark_applied(self, fingerprint: str, result: dict):
        with self._connect() as con:
            con.execute("UPDATE decisions SET applied_at=CURRENT_TIMESTAMP, api_result=? WHERE fingerprint=?",
                        (json.dumps(result, default=str), fingerprint))

    def audit_rows(self) -> list[dict]:
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute("SELECT * FROM decisions ORDER BY decided_at DESC")]
