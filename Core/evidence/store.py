"""Core/evidence/store.py — Evidence store for iterative investigation."""
from __future__ import annotations
import json
import sqlite3
import os
from datetime import datetime
from typing import Any

DB_PATH = os.environ.get("MH_EVIDENCE_DB", os.path.join("GUI", "Reports", "evidence.db"))

class EvidenceStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seed TEXT NOT NULL,
                seed_type TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                summary TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id INTEGER NOT NULL,
                tool_name TEXT NOT NULL,
                target TEXT NOT NULL,
                target_type TEXT NOT NULL,
                result_json TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_url TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_inv ON evidence(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_tool ON evidence(tool_name);

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id INTEGER,
                action TEXT NOT NULL,
                actor TEXT DEFAULT 'system',
                details TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            );

            -- AD-13: Cross-reference schema extension (v2.1)
            -- Extracted entities from evidence result_json for cross-referencing
            CREATE TABLE IF NOT EXISTS evidence_entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (evidence_id) REFERENCES evidence(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_entities_type ON evidence_entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_entities_value ON evidence_entities(entity_value);
            CREATE INDEX IF NOT EXISTS idx_entities_evidence ON evidence_entities(evidence_id);

            -- Cross-reference results: pairs of evidence that share entities
            CREATE TABLE IF NOT EXISTS cross_refs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id INTEGER NOT NULL,
                evidence_id_1 INTEGER NOT NULL,
                evidence_id_2 INTEGER NOT NULL,
                match_type TEXT NOT NULL,
                match_value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (investigation_id) REFERENCES investigations(id),
                FOREIGN KEY (evidence_id_1) REFERENCES evidence(id) ON DELETE CASCADE,
                FOREIGN KEY (evidence_id_2) REFERENCES evidence(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_cross_refs_inv ON cross_refs(investigation_id);
            CREATE INDEX IF NOT EXISTS idx_cross_refs_match ON cross_refs(match_value);
        """)
        conn.commit()
        conn.close()

    def create_investigation(self, seed: str, seed_type: str) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO investigations (seed, seed_type) VALUES (?, ?)",
            (seed, seed_type)
        )
        inv_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO audit_log (investigation_id, action, details) VALUES (?, ?, ?)",
            (inv_id, "created", json.dumps({"seed": seed, "seed_type": seed_type}))
        )
        conn.commit()
        conn.close()
        return inv_id

    def save_evidence(self, investigation_id: int, tool_name: str, target: str,
                      target_type: str, result: dict, confidence: float = 0.5,
                      source_url: str | None = None) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO evidence (investigation_id, tool_name, target, target_type,
               result_json, confidence, source_url) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (investigation_id, tool_name, target, target_type,
             json.dumps(result, ensure_ascii=False), confidence, source_url)
        )
        ev_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO audit_log (investigation_id, action, details) VALUES (?, ?, ?)",
            (investigation_id, "evidence_saved", json.dumps({"evidence_id": ev_id, "tool": tool_name}))
        )
        conn.execute(
            "UPDATE investigations SET updated_at = datetime('now') WHERE id = ?",
            (investigation_id,)
        )
        conn.commit()
        conn.close()
        return ev_id

    def query_evidence(self, investigation_id: int, tool_name: str | None = None) -> list[dict]:
        conn = self._get_conn()
        if tool_name:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE investigation_id = ? AND tool_name = ? ORDER BY created_at DESC",
                (investigation_id, tool_name)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY created_at DESC",
                (investigation_id,)
            ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def get_investigation(self, investigation_id: int) -> dict:
        conn = self._get_conn()
        inv = conn.execute(
            "SELECT * FROM investigations WHERE id = ?", (investigation_id,)
        ).fetchone()
        if not inv:
            conn.close()
            return {"error": "Investigation not found"}
        evidence = conn.execute(
            "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY created_at",
            (investigation_id,)
        ).fetchall()
        audit = conn.execute(
            "SELECT * FROM audit_log WHERE investigation_id = ? ORDER BY timestamp",
            (investigation_id,)
        ).fetchall()
        result = {
            "investigation": dict(inv),
            "evidence": [dict(e) for e in evidence],
            "audit_log": [dict(a) for a in audit],
        }
        conn.close()
        return result

    def list_investigations(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM investigations ORDER BY created_at DESC"
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    # === AD-13: Cross-reference schema methods (v2.1) ===

    def save_entities(self, evidence_id: int, entities: list[dict]) -> int:
        """Save extracted entities for an evidence row.

        Args:
            evidence_id: Evidence row ID
            entities: List of {"entity_type": ..., "entity_value": ..., "confidence": ...}

        Returns:
            Number of entities saved
        """
        if not entities:
            return 0
        conn = self._get_conn()
        saved = 0
        for ent in entities:
            conn.execute(
                """INSERT INTO evidence_entities (evidence_id, entity_type, entity_value, confidence)
                   VALUES (?, ?, ?, ?)""",
                (evidence_id, ent.get("entity_type", "UNKNOWN"),
                 ent.get("entity_value", ""), ent.get("confidence", 0.5))
            )
            saved += 1
        conn.commit()
        conn.close()
        return saved

    def save_cross_ref(self, investigation_id: int, evidence_id_1: int,
                       evidence_id_2: int, match_type: str, match_value: str,
                       confidence: float = 0.5) -> int:
        """Save a cross-reference between two evidence rows."""
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO cross_refs
               (investigation_id, evidence_id_1, evidence_id_2, match_type, match_value, confidence)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (investigation_id, evidence_id_1, evidence_id_2,
             match_type, match_value, confidence)
        )
        ref_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ref_id

    def query_entities(self, investigation_id: int,
                       entity_type: str | None = None) -> list[dict]:
        """Query extracted entities for an investigation.

        Returns:
            List of dicts with evidence_id, entity_type, entity_value, confidence
        """
        conn = self._get_conn()
        if entity_type:
            rows = conn.execute(
                """SELECT ee.* FROM evidence_entities ee
                   JOIN evidence e ON ee.evidence_id = e.id
                   WHERE e.investigation_id = ? AND ee.entity_type = ?
                   ORDER BY ee.entity_value""",
                (investigation_id, entity_type)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT ee.* FROM evidence_entities ee
                   JOIN evidence e ON ee.evidence_id = e.id
                   WHERE e.investigation_id = ?
                   ORDER BY ee.entity_type, ee.entity_value""",
                (investigation_id,)
            ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def query_cross_refs(self, investigation_id: int) -> list[dict]:
        """Query cross-references for an investigation."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM cross_refs
               WHERE investigation_id = ?
               ORDER BY match_type, match_value""",
            (investigation_id,)
        ).fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result
