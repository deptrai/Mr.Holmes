"""Core/Support/consent_tracker.py — Legal consent and usage tracking.

Logs user acceptance of legal disclaimers and records investigation
metadata for compliance purposes.
"""
import os
import json
import time
import hashlib
from datetime import datetime
from pathlib import Path

CONSENT_LOG = os.path.join("GUI", "Reports", "consent_log.jsonl")

class ConsentTracker:
    @staticmethod
    def log_acceptance(username: str, purpose: str, mode: str = "CLI") -> str:
        """Log that a user accepted the legal disclaimer.
        Returns the consent ID."""
        consent_id = hashlib.sha256(
            f"{username}:{purpose}:{time.time()}".encode()
        ).hexdigest()[:16]
        entry = {
            "consent_id": consent_id,
            "username": username,
            "purpose": purpose,
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "unix_time": int(time.time()),
        }
        os.makedirs(os.path.dirname(CONSENT_LOG), exist_ok=True)
        with open(CONSENT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return consent_id
    
    @staticmethod
    def log_investigation(consent_id: str, target: str, target_type: str, 
                          plugins_used: list, result_count: int) -> None:
        """Log investigation metadata for audit trail."""
        entry = {
            "consent_id": consent_id,
            "target_hash": hashlib.sha256(target.encode()).hexdigest()[:16],
            "target_type": target_type,
            "plugins_used": plugins_used,
            "result_count": result_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        with open(CONSENT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    @staticmethod
    def get_history(limit: int = 100) -> list:
        """Read consent history (newest first)."""
        if not os.path.exists(CONSENT_LOG):
            return []
        entries = []
        with open(CONSENT_LOG, "r") as f:
            for line in f:
                entries.append(json.loads(line.strip()))
        return list(reversed(entries))[:limit]
    
    @staticmethod
    def has_recent_consent(username: str, hours: int = 24) -> bool:
        """Check if user has a recent consent on file."""
        if not os.path.exists(CONSENT_LOG):
            return False
        cutoff = time.time() - hours * 3600
        with open(CONSENT_LOG, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("username") == username and entry.get("unix_time", 0) >= cutoff:
                    return True
        return False
