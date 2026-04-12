"""
Core/engine/stage_router.py

Story 9.2 — Multi-Stage BFS Orchestration

StageRouter maps target types to enrichment stages and filters plugins by stage.
Used by StagedProfiler to route clues to the correct plugin set.
"""
from __future__ import annotations

from Core.plugins.base import IntelligencePlugin

# Stage mapping: target_type (uppercase) → stage number
_STAGE_MAP: dict[str, int] = {
    "EMAIL": 2,
    "USERNAME": 2,
    "PHONE": 3,
    "DOMAIN": 3,
    "IP": 3,
}


class StageRouter:
    """
    Routes OSINT clues to enrichment stages based on target type.

    Stage 2: Identity Expansion (EMAIL, USERNAME)
        → Holehe, Maigret, GitHub
    Stage 3: Deep Enrichment (PHONE, DOMAIN, IP)
        → Numverify, Hunter, Shodan
    Stage 1: Fallback (Epic 8 plugins without stage attribute)
    """

    def route(self, target_type: str) -> int:
        """
        Return the stage number for a given target type.

        Args:
            target_type: "EMAIL", "USERNAME", "PHONE", "DOMAIN", "IP", etc.

        Returns:
            2 for EMAIL/USERNAME, 3 for PHONE/DOMAIN/IP, 1 for unknown types.
        """
        return _STAGE_MAP.get(target_type.upper(), 1)

    def filter_plugins(
        self,
        plugins: list[IntelligencePlugin],
        stage: int,
    ) -> list[IntelligencePlugin]:
        """
        Return plugins whose stage attribute matches the given stage.

        Plugins without a 'stage' attribute default to stage 1 (backward compat
        with Epic 8 plugins that predate the stage routing system).

        Args:
            plugins: List of IntelligencePlugin instances.
            stage:   Target stage number (1, 2, or 3).

        Returns:
            Filtered list of plugins for the given stage.
        """
        return [p for p in plugins if getattr(p, "stage", 1) == stage]
