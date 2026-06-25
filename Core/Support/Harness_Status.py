"""
Core/Support/Harness_Status.py

Python wrapper cho harness-cli binary.
Cung cấp trạng thái harness (stats, audit, matrix) dạng Python dict
để các module Mr.Holmes khác query mà không cần shell out thủ công.
"""
import json
import os
import subprocess


class Harness_Status:
    """Wrapper cho scripts/bin/harness-cli."""

    _CLI_REL = os.path.join("scripts", "bin", "harness-cli")

    @staticmethod
    def _cli_path():
        """Resolve harness-cli path relative to repo root."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, Harness_Status._CLI_REL)

    @staticmethod
    def _run(args):
        """Run harness-cli với args, trả về stdout. Raise khi lỗi."""
        cli = Harness_Status._cli_path()
        if not os.path.isfile(cli):
            raise FileNotFoundError(
                "harness-cli not found at %s. Run install-harness.sh first." % cli
            )
        cmd = [cli] + args
        # cwd = repo root (parent of scripts/) so harness-cli finds harness.db
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(cli)))
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "harness-cli %s failed (exit %s): %s"
                % (" ".join(args), proc.returncode, proc.stderr.strip())
            )
        return proc.stdout

    @staticmethod
    def stats():
        """Trả về dict {intakes, stories, decisions, backlog_items, traces}."""
        out = Harness_Status._run(["query", "stats"])
        result = {}
        lines = [
            l for l in out.splitlines()
            if l.strip() and not l.strip().startswith("===") and not l.strip().startswith("---")
        ]
        if len(lines) < 2:
            return result
        header = lines[0].split()
        values = lines[1].split()
        for i, key in enumerate(header):
            if i < len(values):
                try:
                    result[key] = int(values[i])
                except ValueError:
                    result[key] = values[i]
        return result

    @staticmethod
    def audit():
        """Trả về dict {entropy_score, drift_categories}."""
        out = Harness_Status._run(["audit"])
        result = {"entropy_score": None, "drift_categories": {}}
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Entropy score:"):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        result["entropy_score"] = int(parts[2].split("/")[0])
                    except ValueError:
                        pass
            elif line and ":" in line and not line.startswith("==="):
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                # Extract category name before any parenthetical detail
                if "(" in key:
                    key = key.split("(")[0].strip()
                if key in (
                    "Orphaned stories",
                    "Unverified stories",
                    "Unverified decisions",
                    "Open backlog without outcomes",
                    "Stale stories",
                    "Broken tools",
                ):
                    try:
                        result["drift_categories"][key] = int(val.split()[0]) if val else 0
                    except (ValueError, IndexError):
                        result["drift_categories"][key] = val
        return result

    @staticmethod
    def matrix():
        """Trả về list of dicts — story proof rows (numeric mode)."""
        out = Harness_Status._run(["query", "matrix", "--numeric"])
        lines = [l for l in out.splitlines() if l.strip()]
        if len(lines) < 2:
            return []
        header = lines[0].split()
        rows = []
        for line in lines[1:]:
            parts = line.split()
            row = {}
            for i, key in enumerate(header):
                if i < len(parts):
                    try:
                        row[key] = int(parts[i])
                    except ValueError:
                        row[key] = parts[i]
            rows.append(row)
        return rows
