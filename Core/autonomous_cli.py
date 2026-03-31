"""
Core/autonomous_cli.py

Story 8.4 — CLI Menu Integration: Autonomous Profiler (Option 16)

Provides the interactive CLI flow that:
  1. Prompts the user for Target, Type, and Max Depth
  2. Invokes RecursiveProfiler  (Story 8.1)
  3. Invokes MindmapGenerator   (Story 8.3)
  4. Invokes LLMSynthesizer     (Story 8.2)
  5. Persists artifacts into GUI/Reports/Autonomous/<target>/

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
║   Powered by RecursiveProfiler + DeepSeek + vis-network      ║
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
# Input flow  (AC2)
# ─────────────────────────────────────────────────────────────────────────────

class _InputFlow:
    """Collects and validates Target, Type, and Depth from the user."""

    @staticmethod
    def collect() -> tuple[str, str, int]:
        """
        Returns (target, target_type, max_depth).
        Loops until all inputs are valid.
        """
        print(Font.Color.GREEN + _BANNER + Font.Color.RESET)
        print(Font.Color.WHITE + "\n" + "─" * 64)

        # ── Target seed ───────────────────────────────────────────────────
        target = ""
        while not target.strip():
            target = input(
                Font.Color.BLUE + "\n[+]" +
                Font.Color.WHITE + " Nhập mục tiêu OSINT (email / username / IP / domain / phone):\n" +
                Font.Color.GREEN + "    [#MR.HOLMES#]" + Font.Color.WHITE + "--> "
            ).strip()
            if not target:
                _print_err("Mục tiêu không được để trống.")

        # ── Target type ───────────────────────────────────────────────────
        print(
            Font.Color.BLUE + "\n[+]" +
            Font.Color.WHITE + " Chọn loại mục tiêu:"
        )
        for i, t in enumerate(_VALID_TYPES, 1):
            print(f"    {Font.Color.GREEN}{i}{Font.Color.WHITE}. {t}")

        target_type = ""
        while target_type not in _VALID_TYPES:
            raw = input(
                Font.Color.GREEN + "    [#MR.HOLMES#]" +
                Font.Color.WHITE + "--> "
            ).strip().upper()
            # Accept number or name
            if raw.isdigit() and 1 <= int(raw) <= len(_VALID_TYPES):
                target_type = _VALID_TYPES[int(raw) - 1]
            elif raw in _VALID_TYPES:
                target_type = raw
            else:
                _print_err(f"Giá trị không hợp lệ. Nhập 1-{len(_VALID_TYPES)} hoặc tên loại.")

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
# Orchestration  (AC3 + AC4)
# ─────────────────────────────────────────────────────────────────────────────

async def _run_async(target: str, target_type: str, max_depth: int) -> None:
    """
    Full orchestration pipeline: Profiler → Mindmap → LLM → Persist.
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
    manager = PluginManager()
    manager.discover_plugins()
    plugins = manager.plugins

    # Inject API keys from environment using centralized settings
    for p in plugins:
        p.api_key = settings.get_plugin_key(p.name)

    _print_ok(f"Đã tải {len(plugins)} plugins: {', '.join(p.name for p in plugins)}")

    # ── Phase 2: Recursive Profiler ───────────────────────────────────────
    _print_step(2, total_phases, f"Đang quét đệ quy (depth={max_depth})… Có thể mất 10-60s")
    profiler = RecursiveProfiler(max_depth=max_depth)
    graph_dict = await profiler.run_profiler(
        seed_target=target,
        seed_type=target_type,
        plugins=plugins,
    )
    nodes_count = len(graph_dict.get("nodes", []))
    edges_count = len(graph_dict.get("edges", []))
    _print_ok(f"Thu thập hoàn tất: {nodes_count} thực thể, {edges_count} liên kết")

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

    # ── Summary ───────────────────────────────────────────────────────────
    print(Font.Color.WHITE + "\n" + "═" * 64)
    print(Font.Color.GREEN + "🎉 AUTONOMOUS PROFILER HOÀN TẤT!" + Font.Color.WHITE)
    print(f"\n  📁 Thư mục báo cáo: {Font.Color.GREEN}{folder}{Font.Color.WHITE}")
    print(f"  📊 raw_data.json     — {nodes_count} entities, {edges_count} edges")
    print(f"  🌐 mindmap.html      — Biểu đồ tương tác (mở bằng trình duyệt)")
    print(f"  📄 ai_report.md      — Báo cáo phân tích AI")
    print(Font.Color.WHITE + "═" * 64)


# ─────────────────────────────────────────────────────────────────────────────
# Public API  (AC1, AC3)
# ─────────────────────────────────────────────────────────────────────────────

class AutonomousCLI:
    """
    Story 8.4 — Entry point for CLI Option 16: Autonomous Profiler [AI].

    Synchronous wrapper suitable for direct call from Menu.py's main loop.
    """

    @staticmethod
    def run(Mode: str = "Desktop") -> None:  # noqa: ARG002  (Mode reserved for future use)
        """
        Interactive entry point.  Collects input, runs async pipeline,
        then returns control to the menu loop.
        """
        try:
            target, target_type, max_depth = _InputFlow.collect()
            asyncio.run(_run_async(target, target_type, max_depth))
        except KeyboardInterrupt:
            print(Font.Color.RED + "\n\n[!] " + Font.Color.WHITE + "Đã hủy bởi người dùng.")
        except Exception as exc:  # pragma: no cover
            print(Font.Color.RED + "\n[!] " + Font.Color.WHITE +
                  f"Lỗi không mong đợi: {exc}")

        input(Font.Color.GREEN + "\n[ENTER]" + Font.Color.WHITE + " để trở về Menu chính...")
