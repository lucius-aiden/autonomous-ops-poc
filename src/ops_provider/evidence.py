import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any


class EvidenceStore:
    """Small local append-only-ish event store; secrets are never accepted by schema."""

    def __init__(self, path: str | Path = "data/ops-evidence.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, occurred_at TEXT NOT NULL, service TEXT, health_state TEXT, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, opened_at TEXT NOT NULL, service TEXT NOT NULL, condition TEXT NOT NULL, health_state TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL, resolved_at TEXT);
        """)
        self.db.commit()

    def record_event(self, kind: str, occurred_at: str, payload: Any, service: str | None = None, health_state: str | None = None) -> int:
        if self._contains_secret_key(payload):
            raise ValueError("secret-like evidence is not permitted")
        cur = self.db.execute("INSERT INTO events(kind, occurred_at, service, health_state, payload) VALUES (?, ?, ?, ?, ?)", (kind, occurred_at, service, health_state, json.dumps(payload, default=str)))
        self.db.commit()
        return int(cur.lastrowid)

    @staticmethod
    def _contains_secret_key(value: Any) -> bool:
        secret_names = {"privatekey", "agentkey", "password", "token", "secret", "api_key", "apikey"}
        if isinstance(value, dict):
            return any(str(key).lower().replace("-", "_") in secret_names or EvidenceStore._contains_secret_key(item) for key, item in value.items())
        if isinstance(value, list):
            return any(EvidenceStore._contains_secret_key(item) for item in value)
        return False

    def open_incident(self, incident_id: str, opened_at: str, service: str, condition: str, health_state: str, payload: Any) -> None:
        self.db.execute("INSERT INTO incidents VALUES (?, ?, ?, ?, ?, ?, ?, NULL)", (incident_id, opened_at, service, condition, health_state, "OPEN", json.dumps(payload, default=str)))
        self.db.commit()

    def resolve_incident(self, incident_id: str, resolved_at: str, payload: Any) -> None:
        self.db.execute("UPDATE incidents SET status='RESOLVED', resolved_at=?, payload=? WHERE id=?", (resolved_at, json.dumps(payload, default=str), incident_id))
        self.db.commit()

    def events(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM events ORDER BY id")]
