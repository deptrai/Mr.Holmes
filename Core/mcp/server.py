"""Core/mcp/server.py — Mr.Holmes MCP Server.

Exposes OSINT tools via Model Context Protocol for Claude Code integration.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from mcp.server.fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("mr-holmes")

# Lazy-loaded globals
_plugin_manager = None
_settings = None

def _get_plugin_manager():
    global _plugin_manager
    if _plugin_manager is None:
        from Core.plugins.manager import PluginManager
        from Core.config.settings import settings
        _plugin_manager = PluginManager()
        _plugin_manager.discover_plugins()
        for p in _plugin_manager.plugins:
            p.api_key = settings.get_plugin_key(p.name)
    return _plugin_manager

def _get_plugin(name: str):
    pm = _get_plugin_manager()
    return next((p for p in pm.plugins if p.name == name), None)

# === Username OSINT ===

@mcp.tool()
async def search_username(username: str, sites: list[str] | None = None) -> str:
    """Search for a username across 500+ sites.

    Args:
        username: The username to search for
        sites: Optional list of site names to check (None = all sites)

    Returns:
        JSON string with found/not_found/blocked sites
    """
    pm = _get_plugin_manager()
    # Run Maigret plugin for broad coverage
    maigret = _get_plugin("Maigret")
    if maigret:
        result = await maigret.check(username, "username")
        return json.dumps({
            "plugin": "Maigret",
            "is_success": result.is_success,
            "profiles": result.data.get("profiles", []),
            "total_found": result.data.get("total_found", 0),
            "error": result.error_message,
        }, ensure_ascii=False, indent=2)
    return json.dumps({"error": "Maigret plugin not found"})

@mcp.tool()
async def run_maigret(username: str, top_n: int | None = None) -> str:
    """Run Maigret (Sherlock-like) to find username on 500+ sites.

    Args:
        username: Target username
        top_n: Limit to top N sites (None = all 509)

    Returns:
        JSON with profiles found
    """
    maigret = _get_plugin("Maigret")
    if not maigret:
        return json.dumps({"error": "Maigret plugin not found"})
    # Store top_n on plugin instance so check() can use it
    if top_n is not None:
        maigret.top_n = top_n  # type: ignore[attr-defined]
    else:
        maigret.top_n = None  # type: ignore[attr-defined]
    result = await maigret.check(username, "username")
    return json.dumps({
        "is_success": result.is_success,
        "profiles": result.data.get("profiles", []),
        "total_found": result.data.get("total_found", 0),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def scrape_profile(url: str, fields: list[str] | None = None) -> str:
    """Scrape a social media profile page using stealth browser.

    Args:
        url: Profile URL to scrape
        fields: Optional list of fields to extract (None = all)

    Returns:
        JSON with profile data (title, meta tags, content length)
    """
    from Core.browser.stealth_context import scrape_with_stealth, PLAYWRIGHT_AVAILABLE
    if not PLAYWRIGHT_AVAILABLE:
        return json.dumps({
            "error": "Playwright not installed. Run: pip install playwright && playwright install chromium",
            "url": url,
        })
    result = await scrape_with_stealth(url)
    return json.dumps(result, ensure_ascii=False, indent=2)

# === Email OSINT ===

@mcp.tool()
async def search_email(email: str) -> str:
    """Check which services an email is registered on (via Holehe).

    Args:
        email: Email address to check

    Returns:
        JSON with registered sites
    """
    holehe = _get_plugin("Holehe")
    if not holehe:
        return json.dumps({"error": "Holehe plugin not found"})
    result = await holehe.check(email, "email")
    return json.dumps({
        "is_success": result.is_success,
        "registered_sites": result.data.get("registered", []),
        "count": result.data.get("total_registered", 0),
        "recovery_phones": result.data.get("recovery_phones", []),
        "recovery_emails": result.data.get("recovery_emails", []),
        "total_checked": result.data.get("total_checked", 0),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def check_breach(email: str) -> str:
    """Check if email appears in data breaches.

    Tries HaveIBeenPwned first (requires paid key). Falls back to IntelX
    (free tier) if HIBP key is missing.

    Args:
        email: Email to check

    Returns:
        JSON with breach list
    """
    # Try HIBP first
    hibp = _get_plugin("HaveIBeenPwned")
    if hibp and hibp.api_key:
        result = await hibp.check(email, "email")
        if result.is_success:
            return json.dumps({
                "source": "HaveIBeenPwned",
                "is_success": result.is_success,
                "breaches": result.data.get("breach_names", []),
                "count": result.data.get("breach_count", 0),
                "data_classes": result.data.get("data_classes", []),
                "error": result.error_message,
            }, ensure_ascii=False, indent=2)

    # Fallback to IntelX
    intelx = _get_plugin("IntelX")
    if not intelx:
        return json.dumps({"error": "Neither HIBP nor IntelX plugin found"})
    result = await intelx.check(email, "email")
    return json.dumps({
        "source": "IntelX",
        "is_success": result.is_success,
        "breaches": result.data.get("breaches", []),
        "count": result.data.get("breach_count", 0),
        "sources": result.data.get("sources", []),
        "data_classes": result.data.get("data_classes", []),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def check_leak(email: str) -> str:
    """Check for email leaks via LeakLookup.

    Args:
        email: Email to check

    Returns:
        JSON with leak sources
    """
    leak = _get_plugin("LeakLookup")
    if not leak:
        return json.dumps({"error": "LeakLookup plugin not found"})
    result = await leak.check(email, "email")
    return json.dumps({
        "is_success": result.is_success,
        "leaks": result.data.get("leaks", []),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def intelx_search(target: str, target_type: str = "email") -> str:
    """Search Intelligence X for breaches, leaks, and pastes.

    Supports EMAIL, USERNAME, PHONE, DOMAIN, and IP targets.
    Free alternative to HIBP with broader coverage (darknet, pastes, leaks).

    Args:
        target: The search term (email, username, phone, domain, or IP)
        target_type: One of 'email', 'username', 'phone', 'domain', 'ip'

    Returns:
        JSON with breach/leak results
    """
    intelx = _get_plugin("IntelX")
    if not intelx:
        return json.dumps({"error": "IntelX plugin not found"})
    result = await intelx.check(target, target_type)
    return json.dumps({
        "is_success": result.is_success,
        "breaches": result.data.get("breaches", []),
        "count": result.data.get("breach_count", 0),
        "sources": result.data.get("sources", []),
        "data_classes": result.data.get("data_classes", []),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def validate_email(email: str) -> str:
    """Validate email format.

    Args:
        email: Email to validate

    Returns:
        JSON with validation result
    """
    from Core.engine.email_searcher import EmailSearcher
    is_valid = EmailSearcher.validate(email)
    return json.dumps({"email": email, "is_valid": is_valid})

# === Phone OSINT ===

@mcp.tool()
async def search_phone(phone: str) -> str:
    """Look up phone number carrier and location (via Numverify).

    Args:
        phone: Phone number with country code

    Returns:
        JSON with carrier, location, line type
    """
    numverify = _get_plugin("Numverify")
    if not numverify:
        return json.dumps({"error": "Numverify plugin not found"})
    result = await numverify.check(phone, "phone")
    return json.dumps({
        "is_success": result.is_success,
        "carrier": result.data.get("carrier"),
        "location": result.data.get("location"),
        "line_type": result.data.get("line_type"),
        "valid": result.data.get("valid"),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def validate_phone(phone: str) -> str:
    """Validate phone number format.

    Args:
        phone: Phone number

    Returns:
        JSON with validation result
    """
    from Core.engine.phone_searcher import PhoneSearcher
    normalized = PhoneSearcher.normalize_phone(phone)
    return json.dumps({"phone": phone, "normalized": normalized, "is_valid": len(normalized) >= 7})

# === Domain/IP OSINT ===

@mcp.tool()
async def search_domain(domain: str) -> str:
    """Search domain info — DNS, IP, WHOIS.

    Args:
        domain: Domain name (e.g. example.com)

    Returns:
        JSON with DNS records, IP, WHOIS data
    """
    dns = _get_plugin("DNSResolver")
    if not dns:
        return json.dumps({"error": "DNSResolver plugin not found"})
    result = await dns.check(domain, "domain")
    return json.dumps({
        "is_success": result.is_success,
        "ips": result.data.get("ips", []),
        "ns": result.data.get("ns", []),
        "mx": result.data.get("mx", []),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def scan_ports(ip: str, ports: list[int] | None = None) -> str:
    """Scan ports on a host.

    Args:
        ip: IP address or hostname
        ports: Optional list of ports (None = common ports)

    Returns:
        JSON with open ports
    """
    from Core.engine.port_scanner_modern import PortScanner
    results = PortScanner.scan(ip, ports)
    open_ports = [r for r in results if r.get("state") == "open"]
    return json.dumps({
        "host": ip,
        "open_ports": open_ports,
        "total_scanned": len(results),
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def shodan_lookup(ip: str) -> str:
    """Look up IP on Shodan for services and vulnerabilities.

    Args:
        ip: IP address

    Returns:
        JSON with Shodan data
    """
    shodan = _get_plugin("Shodan")
    if not shodan:
        return json.dumps({"error": "Shodan plugin not found"})
    result = await shodan.check(ip, "ip")
    return json.dumps({
        "is_success": result.is_success,
        "data": result.data,
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def whois_lookup(domain: str) -> str:
    """WHOIS lookup for domain registration info.

    Args:
        domain: Domain name

    Returns:
        JSON with registrar, dates, name servers
    """
    # Use SearxNG or direct WHOIS
    import subprocess
    try:
        r = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=10)
        return json.dumps({"domain": domain, "raw": r.stdout[:5000]}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

# === Person OSINT ===

@mcp.tool()
async def search_person(name: str) -> str:
    """Search for a person by name across sources.

    Args:
        name: Person's name

    Returns:
        JSON with found profiles
    """
    # Use SearxNG for person search
    sx = _get_plugin("SearxngOSINT")
    if sx:
        result = await sx.check(name, "person")
        return json.dumps({
            "is_success": result.is_success,
            "results": result.data.get("osint_urls", []),
            "error": result.error_message,
        }, ensure_ascii=False, indent=2)
    return json.dumps({"error": "SearxNG plugin not found"})

@mcp.tool()
async def generate_dorks(target: str, dork_type: str = "google") -> str:
    """Generate Google/Yandex dorks for a target.

    Args:
        target: Search target (username, email, domain)
        dork_type: "google" or "yandex"

    Returns:
        JSON with dork queries
    """
    from Core.engine.dork_generator import DorkGenerator
    if dork_type == "yandex":
        report = DorkGenerator.yandex_dorks(target)
    else:
        report = DorkGenerator.google_dorks(target)
    return json.dumps({"target": target, "type": dork_type, "report_path": report})

@mcp.tool()
async def run_searxng(query: str, category: str = "general") -> str:
    """Run a SearxNG search query.

    Args:
        query: Search query
        category: Search category (general, images, news)

    Returns:
        JSON with search results
    """
    sx = _get_plugin("SearxngOSINT")
    if not sx:
        return json.dumps({"error": "SearxNG plugin not found"})
    result = await sx.check(query, "username")
    return json.dumps({
        "is_success": result.is_success,
        "results": result.data.get("osint_urls", []),
        "metadata": result.data.get("metadata", []),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

# === Entity Resolution ===

@mcp.tool()
async def resolve_entities(entities: str) -> str:
    """Merge duplicate entities into a golden record.

    Args:
        entities: JSON string of entities to merge

    Returns:
        JSON with unified profile
    """
    from Core.engine.entity_resolver import EntityResolver
    resolver = EntityResolver()
    entity_list = json.loads(entities)
    result = await resolver.resolve(entity_list)
    return json.dumps(result.to_dict() if hasattr(result, 'to_dict') else str(result), ensure_ascii=False, indent=2)

@mcp.tool()
async def run_profiler(target: str, target_type: str = "username", max_depth: int = 1) -> str:
    """Run StagedProfiler BFS to expand entities from a seed.

    Args:
        target: Seed target (username, email, etc.)
        target_type: Type of target (username, email, phone, domain)
        max_depth: BFS depth (1-3)

    Returns:
        JSON with profile graph (nodes, edges, results)
    """
    from Core.engine.autonomous_agent import StagedProfiler
    pm = _get_plugin_manager()
    profiler = StagedProfiler(max_depth=max_depth, plugins=pm.plugins)
    result = await profiler.run_staged(target, target_type, plugins=pm.plugins)
    return json.dumps({
        "target": target,
        "target_type": target_type,
        "nodes": result.get("nodes", []),
        "edges": result.get("edges", []),
        "plugin_results": result.get("plugin_results", []),
        "stats": {
            "node_count": len(result.get("nodes", [])),
            "edge_count": len(result.get("edges", [])),
            "result_count": len(result.get("plugin_results", [])),
        }
    }, ensure_ascii=False, indent=2)

# === Evidence Store ===

@mcp.tool()
async def create_investigation(seed: str, seed_type: str) -> str:
    """Create a new investigation case.

    Args:
        seed: Initial target (username, email, phone, etc.)
        seed_type: Type of seed

    Returns:
        JSON with investigation ID
    """
    from Core.evidence.store import EvidenceStore
    store = EvidenceStore()
    inv_id = store.create_investigation(seed, seed_type)
    return json.dumps({"investigation_id": inv_id, "seed": seed, "seed_type": seed_type})

@mcp.tool()
async def save_evidence(investigation_id: int, tool_name: str, target: str, target_type: str, result: str) -> str:
    """Save evidence from a tool call.

    Args:
        investigation_id: Investigation case ID
        tool_name: Name of the tool that produced this evidence
        target: Target that was searched
        target_type: Type of target
        result: JSON string of the tool result

    Returns:
        JSON with evidence ID
    """
    from Core.evidence.store import EvidenceStore
    store = EvidenceStore()
    result_data = json.loads(result)
    evidence_id = store.save_evidence(investigation_id, tool_name, target, target_type, result_data)
    return json.dumps({"evidence_id": evidence_id})

@mcp.tool()
async def query_evidence(investigation_id: int, tool_name: str | None = None) -> str:
    """Query evidence for an investigation.

    Args:
        investigation_id: Investigation case ID
        tool_name: Optional filter by tool name

    Returns:
        JSON with evidence list
    """
    from Core.evidence.store import EvidenceStore
    store = EvidenceStore()
    evidence = store.query_evidence(investigation_id, tool_name)
    return json.dumps({"evidence": evidence, "count": len(evidence)}, ensure_ascii=False, indent=2)

@mcp.tool()
async def get_investigation(investigation_id: int) -> str:
    """Get full investigation with all evidence.

    Args:
        investigation_id: Investigation case ID

    Returns:
        JSON with investigation details and all evidence
    """
    from Core.evidence.store import EvidenceStore
    store = EvidenceStore()
    inv = store.get_investigation(investigation_id)
    return json.dumps(inv, ensure_ascii=False, indent=2)

@mcp.tool()
async def list_investigations() -> str:
    """List all investigations.

    Returns:
        JSON with investigation list
    """
    from Core.evidence.store import EvidenceStore
    store = EvidenceStore()
    invs = store.list_investigations()
    return json.dumps({"investigations": invs, "count": len(invs)}, ensure_ascii=False, indent=2)

# === Utility ===

@mcp.tool()
async def decode_text(text: str, format: str = "base64") -> str:
    """Decode text (base64, md5, sha256).

    Args:
        text: Text to decode/hash
        format: "base64" (decode), "base64_encode", "md5", "sha256"

    Returns:
        JSON with decoded/hashed result
    """
    from Core.engine.decoder_util import DecoderUtil
    if format == "base64":
        result = DecoderUtil.base64_decode(text)
    elif format == "base64_encode":
        result = DecoderUtil.base64_encode(text)
    elif format == "md5":
        result = DecoderUtil.md5_hash(text)
    elif format == "sha256":
        result = DecoderUtil.sha256_hash(text)
    else:
        return json.dumps({"error": f"Unknown format: {format}"})
    return json.dumps({"input": text, "format": format, "output": result})

@mcp.tool()
async def list_plugins() -> str:
    """List all available OSINT plugins.

    Returns:
        JSON with plugin list
    """
    pm = _get_plugin_manager()
    return json.dumps({
        "plugins": [
            {
                "name": p.name,
                "requires_api_key": p.requires_api_key,
                "stage": getattr(p, "stage", 1),
                "has_key": bool(getattr(p, "api_key", "")),
            }
            for p in pm.plugins
        ],
        "count": len(pm.plugins),
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def run_plugin(plugin_name: str, target: str, target_type: str) -> str:
    """Run a specific plugin by name.

    Args:
        plugin_name: Name of the plugin (e.g. "GitHub", "DNSResolver")
        target: Target to check
        target_type: Type of target (username, email, phone, domain, ip)

    Returns:
        JSON with plugin result
    """
    plugin = _get_plugin(plugin_name)
    if not plugin:
        return json.dumps({"error": f"Plugin '{plugin_name}' not found"})
    result = await plugin.check(target, target_type)
    return json.dumps({
        "plugin": plugin.name,
        "target": target,
        "target_type": target_type,
        "is_success": result.is_success,
        "data": result.data,
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

# === v2.1: Engine Module Wire ===

@mcp.tool()
async def synthesize_report(investigation_id: int) -> str:
    """Generate an LLM-synthesized narrative report from investigation evidence.

    Collects all evidence for an investigation, builds a ProfileGraph dict,
    and calls the LLM synthesizer to produce a Markdown analyst report.

    Args:
        investigation_id: The investigation ID

    Returns:
        JSON with report_markdown, model_used, is_success
    """
    from Core.engine.llm_synthesizer import LLMSynthesizer
    from Core.evidence.store import EvidenceStore

    store = EvidenceStore()
    inv = store.get_investigation(investigation_id)
    if "error" in inv:
        return json.dumps({"error": inv["error"]}, ensure_ascii=False)

    evidence_rows = inv.get("evidence", [])
    if not evidence_rows:
        return json.dumps({"error": "No evidence found for investigation"}, ensure_ascii=False)

    # Build ProfileGraph dict from evidence
    nodes: list[dict] = []
    edges: list[dict] = []
    plugin_results: list[dict] = []
    seen_targets: set[str] = set()

    for ev in evidence_rows:
        target = ev.get("target", "")
        target_type = ev.get("target_type", "UNKNOWN")
        tool = ev.get("tool_name", "unknown")
        try:
            data = json.loads(ev.get("result_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            data = {}

        if target and target not in seen_targets:
            nodes.append({"target": target, "target_type": target_type.upper(), "depth": 0 if target == inv["investigation"].get("seed") else 1})
            seen_targets.add(target)

        plugin_results.append({
            "plugin": tool,
            "target": target,
            "is_success": bool(data),
            "data": data,
        })

    graph = {"nodes": nodes, "edges": edges, "plugin_results": plugin_results}

    synth = LLMSynthesizer()
    result = await synth.synthesize(graph)
    return json.dumps({
        "is_success": result.is_success,
        "report_markdown": result.report_markdown,
        "model_used": result.model_used,
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def export_pdf(investigation_id: int, template: int = 1) -> str:
    """Export an investigation report to HTML/PDF.

    Generates an HTML report from investigation evidence using PDFBuilder.

    Args:
        investigation_id: The investigation ID
        template: Template number (1=LIGHT, 2=DARK, 3=HIGH-CONTRAST)

    Returns:
        JSON with file_path and html_content
    """
    from Core.engine.pdf_builder import PDFBuilder
    from Core.evidence.store import EvidenceStore

    store = EvidenceStore()
    inv = store.get_investigation(investigation_id)
    if "error" in inv:
        return json.dumps({"error": inv["error"]}, ensure_ascii=False)

    evidence_rows = inv.get("evidence", [])
    if not evidence_rows:
        return json.dumps({"error": "No evidence found"}, ensure_ascii=False)

    # Build content from evidence
    lines = ["<h2>Evidence Report</h2>"]
    for ev in evidence_rows:
        lines.append(
            f"<div class='evidence'><h3>{ev.get('tool_name', '?')} → "
            f"{ev.get('target', '?')} ({ev.get('target_type', '?')})</h3>"
            f"<pre>{ev.get('result_json', '')}</pre></div>"
        )
    content = "\n".join(lines)
    seed = inv["investigation"].get("seed", "unknown")
    html = PDFBuilder.generate_html(seed, content, template)

    # Save to file
    import os
    report_dir = os.path.join("GUI", "Reports", "Investigations", str(investigation_id))
    os.makedirs(report_dir, exist_ok=True)
    file_path = os.path.join(report_dir, f"{seed}_report.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    return json.dumps({
        "is_success": True,
        "file_path": file_path,
        "html_length": len(html),
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def generate_mindmap(investigation_id: int) -> str:
    """Generate an interactive HTML mindmap from investigation evidence.

    Creates a vis-network mindmap showing entity relationships.

    Args:
        investigation_id: The investigation ID

    Returns:
        JSON with file_path
    """
    from Core.engine.mindmap_generator import MindmapGenerator
    from Core.evidence.store import EvidenceStore

    store = EvidenceStore()
    inv = store.get_investigation(investigation_id)
    if "error" in inv:
        return json.dumps({"error": inv["error"]}, ensure_ascii=False)

    evidence_rows = inv.get("evidence", [])
    if not evidence_rows:
        return json.dumps({"error": "No evidence found"}, ensure_ascii=False)

    # Build graph from evidence
    nodes: list[dict] = []
    edges: list[dict] = []
    seen: set[str] = set()
    seed = inv["investigation"].get("seed", "unknown")

    for ev in evidence_rows:
        target = ev.get("target", "")
        ttype = ev.get("target_type", "UNKNOWN").upper()
        tool = ev.get("tool_name", "unknown")
        if target and target not in seen:
            nodes.append({"target": target, "target_type": ttype, "depth": 0 if target == seed else 1})
            seen.add(target)
            if target != seed:
                edges.append({"source": seed, "discovered": target, "via_plugin": tool, "type": "found"})

    graph = {"nodes": nodes, "edges": edges, "plugin_results": []}
    gen = MindmapGenerator()
    html = gen.generate(graph)

    import os
    report_dir = os.path.join("GUI", "Reports", "Investigations", str(investigation_id))
    os.makedirs(report_dir, exist_ok=True)
    file_path = os.path.join(report_dir, f"{seed}_mindmap.html")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)

    return json.dumps({
        "is_success": True,
        "file_path": file_path,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }, ensure_ascii=False, indent=2)

# === v2.1: Cross-Reference Engine ===

@mcp.tool()
async def cross_reference(investigation_id: int) -> str:
    """Cross-reference evidence in an investigation to find overlaps and suggest new targets.

    Analyzes all evidence rows for:
    - Emails/usernames/phones appearing in multiple evidence
    - Clues extracted from breach data, scrape results
    - Suggested new targets to investigate

    Args:
        investigation_id: The investigation ID

    Returns:
        JSON with overlaps and suggested_targets
    """
    import re
    from Core.evidence.store import EvidenceStore

    store = EvidenceStore()
    inv = store.get_investigation(investigation_id)
    if "error" in inv:
        return json.dumps({"error": inv["error"]}, ensure_ascii=False)

    evidence_rows = inv.get("evidence", [])
    if not evidence_rows:
        return json.dumps({"error": "No evidence found"}, ensure_ascii=False)

    # Collect all entities by type
    entities: dict[str, set[str]] = {"EMAIL": set(), "USERNAME": set(), "PHONE": set(), "DOMAIN": set(), "NAME": set()}
    target_to_evidence: dict[str, list[int]] = {}

    email_pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
    phone_pattern = re.compile(r'\+?\d[\d\s\-]{8,15}\d')

    for ev in evidence_rows:
        target = ev.get("target", "")
        ttype = ev.get("target_type", "").upper()
        ev_id = ev.get("id", 0)
        result_json = ev.get("result_json", "{}")

        # Track target → evidence mapping
        if target not in target_to_evidence:
            target_to_evidence[target] = []
        target_to_evidence[target].append(ev_id)

        # Add target to entities
        if ttype in entities:
            entities[ttype].add(target)

        # Extract clues from result_json
        try:
            data = json.loads(result_json)
        except (json.JSONDecodeError, TypeError):
            data = {}

        # Extract emails from result data
        result_str = json.dumps(data)
        found_emails = set(email_pattern.findall(result_str))
        for email in found_emails:
            entities["EMAIL"].add(email)

        # Extract names from scrape results
        for key in ("name", "full_name", "real_names", "keywords"):
            val = data.get(key)
            if isinstance(val, str) and len(val) > 2:
                entities["NAME"].add(val)
            elif isinstance(val, list):
                for v in val:
                    if isinstance(v, str) and len(v) > 2:
                        entities["NAME"].add(v)

    # Find overlaps: targets appearing in multiple evidence rows
    overlaps: list[dict] = []
    for target, ev_ids in target_to_evidence.items():
        if len(ev_ids) > 1:
            overlaps.append({"target": target, "evidence_ids": ev_ids, "count": len(ev_ids)})

    # Suggest new targets: entities not yet investigated
    investigated = set(target_to_evidence.keys())
    suggested: list[dict] = []
    for ttype, values in entities.items():
        for val in values:
            if val and val not in investigated:
                suggested.append({"target": val, "target_type": ttype, "reason": "Found in evidence data"})

    return json.dumps({
        "investigation_id": investigation_id,
        "total_evidence": len(evidence_rows),
        "overlaps": overlaps,
        "overlap_count": len(overlaps),
        "suggested_targets": suggested[:20],
        "suggestion_count": len(suggested),
        "entities_found": {k: len(v) for k, v in entities.items()},
    }, ensure_ascii=False, indent=2)

# === v2.1: Vietnam OSINT Plugins ===

@mcp.tool()
async def search_tax(tax_id: str) -> str:
    """Look up Vietnam tax code (mã số thuế) via XInvoice API.

    Args:
        tax_id: 10-13 digit tax code

    Returns:
        JSON with taxpayer name, address, status
    """
    intelx = _get_plugin("XInvoice")
    if not intelx:
        return json.dumps({"error": "XInvoice plugin not found"})
    result = await intelx.check(tax_id, "tax_id")
    return json.dumps({
        "is_success": result.is_success,
        "data": result.data,
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def search_court_records(name: str) -> str:
    """Search Vietnam court records by name.

    Args:
        name: Person or company name (Vietnamese)

    Returns:
        JSON with matching court cases
    """
    plugin = _get_plugin("VnCourt")
    if not plugin:
        return json.dumps({"error": "VnCourt plugin not found"})
    result = await plugin.check(name, "name")
    return json.dumps({
        "is_success": result.is_success,
        "cases": result.data.get("cases", []),
        "count": result.data.get("count", 0),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def search_news(query: str, date_from: str = "", date_to: str = "") -> str:
    """Search Vietnam news archives for articles mentioning a person or company.

    Uses Google News + site-specific dorks for tuoitre.vn, vnexpress.net, thanhnien.vn.

    Args:
        query: Person name or company name
        date_from: Optional start date (YYYY-MM-DD)
        date_to: Optional end date (YYYY-MM-DD)

    Returns:
        JSON with article list
    """
    plugin = _get_plugin("VnNews")
    if not plugin:
        return json.dumps({"error": "VnNews plugin not found"})
    result = await plugin.check(query, "name")
    return json.dumps({
        "is_success": result.is_success,
        "articles": result.data.get("articles", []),
        "count": result.data.get("count", 0),
        "error": result.error_message,
    }, ensure_ascii=False, indent=2)

# === Entry point ===

def main():
    """Run MCP server on stdio transport."""
    mcp.run()

if __name__ == "__main__":
    main()
