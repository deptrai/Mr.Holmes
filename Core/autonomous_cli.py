"""
Core/autonomous_cli.py

Story 8.4 — CLI Menu Integration: Autonomous Profiler (Option 16)
Story 9.6 — Complete Profile Mode: seed type auto-detection, ToS Risk Summary,
            golden_record.json output, graceful degradation.

Provides the interactive CLI flow that:
  1. Prompts the user for Target (auto-detects type), and Max Depth
  2. Displays ToS Risk Summary for loaded plugins
  3. Invokes StagedProfiler (Story 9.2) or RecursiveProfiler (Story 8.1)
  4. Invokes MindmapGenerator   (Story 8.3)
  5. Invokes LLMSynthesizer     (Story 8.2)
  6. Builds ProfileEntity (Story 9.1) and saves golden_record.json
  7. Persists artifacts into GUI/Reports/Autonomous/<target>/

Usage (from Menu.py dispatcher)::

    from Core import autonomous_cli
    autonomous_cli.AutonomousCLI.run(Mode)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timezone

from Core.Support import Font
from Core.config import settings  # noqa: F401 — triggers .env load at import time


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

_VALID_TYPES = ["EMAIL", "USERNAME", "IP", "DOMAIN", "PHONE"]
_REPORT_BASE = os.path.join("GUI", "Reports", "Autonomous")

_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║   🤖  AUTONOMOUS PROFILER  [AI-POWERED OSINT ENGINE]  🤖     ║
║   Powered by StagedProfiler + DeepSeek + vis-network         ║
╚══════════════════════════════════════════════════════════════╝"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_folder_name(target: str) -> str:
    """Sanitize target string into a filesystem-safe directory name."""
    return re.sub(r'[<>:"/\\|?*\s]', "_", target)[:80]


def _print_step(n: int, total: int, msg: str) -> None:
    print(
        Font.Color.GREEN + f"\n[Phase {n}/{total}] " +
        Font.Color.WHITE + msg
    )


def _print_ok(msg: str) -> None:
    print(Font.Color.GREEN + "  ✅ " + Font.Color.WHITE + msg)


def _print_info(msg: str) -> None:
    print(Font.Color.BLUE + "  [*] " + Font.Color.WHITE + msg)


def _print_err(msg: str) -> None:
    print(Font.Color.RED + "  [!] " + Font.Color.WHITE + msg)


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.6 — Seed type auto-detection  (AC1)
# ─────────────────────────────────────────────────────────────────────────────

_IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def detect_seed_type(seed: str) -> str:
    """
    Auto-detect seed type from string pattern.

    Rules:
    - Contains '@'                        → EMAIL
    - Starts with '+' or all digits,
      length 9-15 chars                  → PHONE
    - Matches IPv4 pattern               → IP
    - Contains '.' but no '@' and not IP → DOMAIN
    - Otherwise                          → USERNAME
    """
    seed = seed.strip()
    if "@" in seed:
        return "EMAIL"
    if re.match(r"^\+?\d{9,15}$", seed):
        return "PHONE"
    if _IPV4_RE.match(seed) and all(0 <= int(o) <= 255 for o in seed.split(".")):
        return "IP"
    if "." in seed:
        return "DOMAIN"
    return "USERNAME"


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.6 — ToS Risk Summary display  (AC2)
# ─────────────────────────────────────────────────────────────────────────────

def _display_tos_summary(plugins: list) -> bool:
    """
    Display a ToS risk table for all loaded plugins.
    Returns True if user confirms to proceed, False to cancel.

    Uses Rich Table if available, falls back to plain text.
    """
    _TOS_LABELS = {
        "safe":     "✓ Safe",
        "tos_risk": "⚠ ToS Risk",
        "ban_risk":  "⛔ Ban Risk",
    }

    # Try Rich first
    try:
        from rich.table import Table
        from rich.console import Console

        console = Console()
        table = Table(title="Complete Profile Mode — Risk Summary")
        table.add_column("Plugin", style="cyan")
        table.add_column("Stage", justify="center")
        table.add_column("ToS Risk", justify="center")

        for plugin in plugins:
            risk = getattr(plugin, "tos_risk", "safe")
            stage = str(getattr(plugin, "stage", 1))
            risk_display = {
                "safe":     "[green]✓ Safe[/green]",
                "tos_risk": "[yellow]⚠ ToS Risk[/yellow]",
                "ban_risk":  "[red]⛔ Ban Risk[/red]",
            }.get(risk, risk)
            table.add_row(plugin.name, stage, risk_display)

        console.print(table)
    except ImportError:
        # Fallback plain text table
        print(Font.Color.WHITE + "\n╔══════════════════════════════════════╗")
        print(Font.Color.WHITE +   "║  Complete Profile Mode — Risk Summary ║")
        print(Font.Color.WHITE +   "╚══════════════════════════════════════╝")
        print(f"  {'Plugin':<20} {'Stage':>5}  {'ToS Risk'}")
        print("  " + "─" * 37)
        for plugin in plugins:
            risk = getattr(plugin, "tos_risk", "safe")
            stage = getattr(plugin, "stage", 1)
            label = _TOS_LABELS.get(risk, risk)
            print(f"  {plugin.name:<20} {stage:>5}  {label}")
        print("  " + "─" * 37)

    confirm = input(Font.Color.WHITE + "\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        return False

    # AC2: ban_risk plugins require explicit separate confirmation
    ban_risk_plugins = [p for p in plugins if getattr(p, "tos_risk", "safe") == "ban_risk"]
    for p in ban_risk_plugins:
        ban_confirm = input(
            Font.Color.RED + f"\n⛔ {p.name}" +
            Font.Color.WHITE + " has ban risk. Explicitly confirm? (y/n): "
        ).strip().lower()
        if ban_confirm != "y":
            return False

    return True


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.6 — ProfileEntity builder from ProfileGraph  (AC4, AC5)
# ─────────────────────────────────────────────────────────────────────────────

def _build_profile_entity(graph_data: dict, seed: str, seed_type: str):
    """
    Build a ProfileEntity (Story 9.1) from ProfileGraph plugin_results dict.

    Extracts:
    - real_names  : from Maigret profiles[].name
    - breach_sources : from HIBP breach_names and LeakLookup hostnames
    - platforms   : from Maigret profiles[].site → url
    - sources     : plugin names that contributed

    Returns a ProfileEntity with confidence recalculated from real_names.
    """
    from Core.models.profile_entity import ProfileEntity, SourcedField

    entity = ProfileEntity(seed=seed, seed_type=seed_type)

    for pr in graph_data.get("plugin_results", []):
        if not pr.get("is_success"):
            continue
        plugin = pr.get("plugin", "unknown")
        data = pr.get("data", {})

        # Extract real names from Maigret profiles
        profiles = data.get("profiles") or []
        for profile in profiles:
            name = profile.get("name", "").strip()
            if name:
                # F10: deduplicate by value
                existing_names = {f.value for f in entity.real_names}
                if name not in existing_names:
                    entity.real_names.append(SourcedField(
                        value=name,
                        source=f"{plugin}/{profile.get('site', '')}",
                        confidence=0.7,
                    ))

        # Extract emails from GitHub plugin data
        for email in (data.get("emails") or []):
            existing_emails = {f.value for f in entity.emails}
            if email and isinstance(email, str) and email not in existing_emails:
                entity.emails.append(SourcedField(
                    value=email,
                    source=plugin,
                    confidence=0.8,
                ))

        # Extract breach sources from HIBP breach_names
        for breach in (data.get("breach_names") or []):
            if breach not in entity.breach_sources:
                entity.breach_sources.append(breach)

        # Extract breach sources from LeakLookup hostnames
        for src in (data.get("hostnames") or []):
            if src not in entity.breach_sources:
                entity.breach_sources.append(src)

        # Extract platforms from Maigret profiles
        for profile in profiles:
            site = profile.get("site", "").lower()
            url = profile.get("url", "")
            if site and url:
                entity.platforms.setdefault(site, url)

        # Track contributing sources
        if plugin not in entity.sources:
            entity.sources.append(plugin)

    # Recalculate confidence from all populated fields
    all_fields = entity.real_names + entity.emails + entity.phones + entity.usernames
    if all_fields:
        entity.confidence = sum(f.confidence for f in all_fields) / len(all_fields)

    return entity


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.6 — Progress display  (AC3)
# ─────────────────────────────────────────────────────────────────────────────

_STAGE_LABELS = {
    1: "Breach Intelligence",
    2: "Identity Expansion",
    3: "Deep Verification",
}


def _print_progress_summary(graph_dict: dict) -> None:
    """Print per-plugin result summary grouped by stage after profiling completes."""
    plugin_results = graph_dict.get("plugin_results", [])
    if not plugin_results:
        return

    # Group results by stage
    by_stage: dict[int, list[dict]] = {}
    for pr in plugin_results:
        stage = pr.get("stage", 1)
        by_stage.setdefault(stage, []).append(pr)

    for stage in sorted(by_stage):
        label = _STAGE_LABELS.get(stage, f"Stage {stage}")
        print(Font.Color.WHITE + f"\n  [●] Stage {stage} — {label}")
        for pr in by_stage[stage]:
            name = pr.get("plugin", "unknown")
            ok = pr.get("is_success", False)
            data = pr.get("data") or {}

            # Build a short summary from data
            parts = []
            if "registered" in data:
                parts.append(f"{len(data['registered'])} services found")
            if "profiles" in data:
                parts.append(f"{len(data['profiles'])} profiles found")
            if "breach_names" in data:
                parts.append(f"{len(data['breach_names'])} breaches")
            if "hostnames" in data:
                parts.append(f"{len(data['hostnames'])} sources")

            detail = ", ".join(parts) if parts else (pr.get("error", "") or "no data")
            icon = Font.Color.GREEN + "    ✓" if ok else Font.Color.RED + "    ✗"
            print(f"{icon} {Font.Color.WHITE}{name:<20}: {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# Input flow  (AC1 — Story 9.6 updated)
# ─────────────────────────────────────────────────────────────────────────────

class _InputFlow:
    """
    Collects and validates Target, Type, and Depth from the user.

    Story 9.6: auto-detects seed type from input string, then
    confirms with user before proceeding.
    """

    @staticmethod
    def collect() -> tuple[str, str, int]:
        """
        Returns (target, target_type, max_depth).
        Loops until all inputs are valid.
        """
        print(Font.Color.GREEN + _BANNER + Font.Color.RESET)
        print(Font.Color.WHITE + "\n" + "─" * 64)

        # ── Target seed (auto-detect type) ────────────────────────────────
        target = ""
        target_type = ""
        while not target.strip():
            target = input(
                Font.Color.BLUE + "\n[+]" +
                Font.Color.WHITE + " Enter target (email / username / phone):\n" +
                Font.Color.GREEN + "    [#MR.HOLMES#]" + Font.Color.WHITE + "--> "
            ).strip()
            if not target:
                _print_err("Mục tiêu không được để trống.")
                continue

            # Auto-detect type
            detected = detect_seed_type(target)
            confirm = input(
                Font.Color.BLUE + f"\n[?]" +
                Font.Color.WHITE + f" Detected type: {detected}. Continue? (y/n): "
            ).strip().lower()
            if confirm != "y":
                _print_info("Nhập lại mục tiêu.")
                target = ""
            else:
                target_type = detected

        # target_type is set inside the confirm branch above

        # ── Max depth ─────────────────────────────────────────────────────
        max_depth = -1
        while max_depth < 0 or max_depth > 3:
            raw = input(
                Font.Color.BLUE + "\n[+]" +
                Font.Color.WHITE + " Chiều sâu đệ quy tối đa [0-3] (mặc định: 1):\n" +
                Font.Color.GREEN + "    [#MR.HOLMES#]" + Font.Color.WHITE + "--> "
            ).strip()
            if raw == "":
                max_depth = 1
                break
            try:
                max_depth = int(raw)
                if max_depth < 0 or max_depth > 3:
                    _print_err("Chiều sâu phải nằm trong khoảng [0, 3].")
            except ValueError:
                _print_err("Vui lòng nhập số nguyên.")

        print(Font.Color.WHITE + "\n" + "─" * 64)
        print(
            Font.Color.GREEN + "[✓] Cấu hình xác nhận:" +
            Font.Color.WHITE +
            f"\n    Mục tiêu  : {target}" +
            f"\n    Loại      : {target_type}" +
            f"\n    Độ sâu    : {max_depth}"
        )
        print(Font.Color.WHITE + "─" * 64)
        return target, target_type, max_depth


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration  (AC3, AC4, AC5, AC6 — Story 9.6 updated)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_async(
    target: str,
    target_type: str,
    max_depth: int,
    plugins: list | None = None,
) -> None:
    """
    Full orchestration pipeline: Profiler → Mindmap → LLM → Persist.

    Story 9.6:
    - Accepts optional pre-loaded plugins (avoids double discovery).
    - Prints per-plugin progress summary after profiling.
    - Builds ProfileEntity and saves golden_record.json.
    - Shows graceful degradation hint when Epic 9 plugins absent.

    Runs entirely async so it can be called via asyncio.run().
    """
    # Lazy imports to avoid circular deps and slow startup
    from Core.plugins.manager import PluginManager
    from Core.engine.autonomous_agent import RecursiveProfiler
    from Core.engine.mindmap_generator import MindmapGenerator
    from Core.engine.llm_synthesizer import LLMSynthesizer

    total_phases = 4

    # ── Phase 1: Load plugins ─────────────────────────────────────────────
    _print_step(1, total_phases, "Tải Intelligence Plugins...")
    if plugins is None:
        manager = PluginManager()
        manager.discover_plugins()
        plugins = manager.plugins
        for p in plugins:
            p.api_key = settings.get_plugin_key(p.name)

    _print_ok(f"Đã tải {len(plugins)} plugins: {', '.join(p.name for p in plugins)}")

    # Story 9.6 AC8 — graceful degradation hint
    plugin_names = {p.name.lower() for p in plugins}
    has_epic9 = "holehe" in plugin_names or "maigret" in plugin_names
    if not has_epic9:
        _print_info("Note: Install holehe and maigret for deeper profiling")

    # ── Phase 2: Profiler (staged if Epic 9 plugins present, flat otherwise) ─
    _print_step(2, total_phases, f"Đang quét đệ quy (depth={max_depth})… Có thể mất 10-60s")
    has_staged_plugins = any(getattr(p, "stage", 1) >= 2 for p in plugins)
    if has_staged_plugins:
        from Core.engine.autonomous_agent import StagedProfiler
        profiler = StagedProfiler(max_depth=max_depth)
        graph_dict = await profiler.run_staged(
            seed_target=target,
            seed_type=target_type,
            plugins=plugins,
        )
    else:
        profiler = RecursiveProfiler(max_depth=max_depth)
        graph_dict = await profiler.run_profiler(
            seed_target=target,
            seed_type=target_type,
            plugins=plugins,
        )
    nodes_count = len(graph_dict.get("nodes", []))
    edges_count = len(graph_dict.get("edges", []))
    _print_ok(f"Thu thập hoàn tất: {nodes_count} thực thể, {edges_count} liên kết")

    # Story 9.6 AC3 — progress summary
    _print_progress_summary(graph_dict)

    # ── Phase 3: Mindmap ──────────────────────────────────────────────────
    _print_step(3, total_phases, "Tạo HTML Mindmap tương tác…")
    gen = MindmapGenerator()
    html_content = gen.generate(graph_dict)
    _print_ok("Mindmap HTML đã sẵn sàng")

    # ── Phase 4: LLM Synthesis ────────────────────────────────────────────
    _print_step(4, total_phases, "Đang gửi dữ liệu cho LLM tổng hợp Báo Cáo AI…")
    synth = LLMSynthesizer()
    result = await synth.synthesize(graph_dict)

    if result.is_success:
        _print_ok(f"Báo cáo LLM hoàn tất (model: {result.model_used})")
    else:
        _print_err(f"LLM thất bại: {result.error_message}")
        _print_info("Tiếp tục lưu dữ liệu thô và mindmap…")

    # ── Persist artifacts (AC4) ───────────────────────────────────────────
    folder = os.path.join(_REPORT_BASE, _safe_folder_name(target))
    os.makedirs(folder, exist_ok=True)

    # raw_data.json
    json_path = os.path.join(folder, "raw_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(graph_dict, f, ensure_ascii=False, indent=2)

    # mindmap.html
    html_path = os.path.join(folder, "mindmap.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # ai_report.md
    report_md = result.report_markdown if result.is_success else (
        f"# OSINT Report — {target}\n\n"
        f"> ⚠️ LLM synthesis failed: {result.error_message}\n\n"
        f"## Raw Entity Count\n- Nodes: {nodes_count}\n- Edges: {edges_count}\n"
    )
    md_path = os.path.join(folder, "ai_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # Story 9.6 AC5 — golden_record.json
    entity = _build_profile_entity(graph_dict, target, target_type)
    golden_path = os.path.join(folder, "golden_record.json")
    with open(golden_path, "w", encoding="utf-8") as f:
        json.dump(entity.to_dict(), f, ensure_ascii=False, indent=2)
    _print_ok(
        f"Golden Record: confidence={entity.confidence:.2f}, "
        f"{len(entity.real_names)} names, {len(entity.breach_sources)} breaches"
    )

    # ── Summary ───────────────────────────────────────────────────────────
    print(Font.Color.WHITE + "\n" + "═" * 64)
    print(Font.Color.GREEN + "🎉 AUTONOMOUS PROFILER HOÀN TẤT!" + Font.Color.WHITE)
    print(f"\n  📁 Thư mục báo cáo: {Font.Color.GREEN}{folder}{Font.Color.WHITE}")
    print(f"  📊 raw_data.json     — {nodes_count} entities, {edges_count} edges")
    print(f"  🌐 mindmap.html      — Biểu đồ tương tác (mở bằng trình duyệt)")
    print(f"  📄 ai_report.md      — Báo cáo phân tích AI")
    print(f"  🧬 golden_record.json — Golden Record (ProfileEntity)")
    print(Font.Color.WHITE + "═" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Public API  (AC1, AC3)
# ─────────────────────────────────────────────────────────────────────────────

class AutonomousCLI:
    """
    Story 8.4 — Entry point for CLI Option 16: Autonomous Profiler [AI].
    Story 9.6 — Updated: ToS Risk Summary, auto-detect seed type.

    Synchronous wrapper suitable for direct call from Menu.py's main loop.
    """

    @staticmethod
    def run(Mode: str = "Desktop") -> None:  # noqa: ARG002  (Mode reserved for future use)
        """
        Interactive entry point. Collects input, shows ToS summary,
        runs async pipeline, then returns control to the menu loop.
        """
        try:
            target, target_type, max_depth = _InputFlow.collect()

            # Load plugins for ToS summary display
            from Core.plugins.manager import PluginManager
            manager = PluginManager()
            manager.discover_plugins()
            plugins = manager.plugins
            for p in plugins:
                p.api_key = settings.get_plugin_key(p.name)

            # Story 9.6 AC2 — ToS Risk Summary confirmation
            if not _display_tos_summary(plugins):
                print(Font.Color.RED + "\n[!] " + Font.Color.WHITE + "Đã hủy bởi người dùng.")
            else:
                asyncio.run(_run_async(target, target_type, max_depth, plugins=plugins))

        except KeyboardInterrupt:
            print(Font.Color.RED + "\n\n[!] " + Font.Color.WHITE + "Đã hủy bởi người dùng.")
        except Exception as exc:  # pragma: no cover
            print(Font.Color.RED + "\n[!] " + Font.Color.WHITE +
                  f"Lỗi không mong đợi: {exc}")

        input(Font.Color.GREEN + "\n[ENTER]" + Font.Color.WHITE + " để trở về Menu chính...")
