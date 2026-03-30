# Story 8.3: Interactive Mindmap Generation

Status: review

## Story
**As an** OSINT Investigator
**I want** to visualize the recursive reconnaissance data as an interactive HTML mindmap (Network Graph)
**so that** I can intuitively explore the relationships between entities, see the deep connections, and present the data visually to stakeholders.

## Acceptance Criteria
- AC1: Provide a class `MindmapGenerator` in `Core/engine/mindmap_generator.py` that takes a ProfileGraph dictionary.
- AC2: Generate a standalone HTML file that renders the nodes and edges using an interactive library like **vis-network (Vis.js)**.
- AC3: The HTML file must embed the graph data directly (no external local JSON file loading required) so the report is fully portable.
- AC4: Nodes should be visually distinct (e.g. colors, shapes) based on `target_type` (EMAIL, DOMAIN, IP, etc.) and `depth`.
- AC5: Edges should display the `plugin` name that discovered the connection as the edge label.
- AC6: The module must handle empty graphs smoothly.
- AC7: Have appropriate unit tests.

## Tasks/Subtasks
- [x] 1. Define standard Vis.js HTML template (string or file) loading `vis-network` from CDN.
- [x] 2. Create `MindmapGenerator` class in `Core/engine/mindmap_generator.py`.
- [x] 3. Implement graph data serialization (convert backend nodes/edges to Vis.js nodes/edges format).
- [x] 4. Implement HTML file generation logic embedding the serialized JSON via `.replace()` or Jinja2.
- [x] 5. Write unit tests for `MindmapGenerator` (`tests/engine/test_mindmap_generator.py`).
- [x] 6. Update `demo_story8_2.py` to also output an `output_mindmap.html` to visually verify.

## Dev Notes
- **Architecture**: The `MindmapGenerator` should be fully decoupled from the RecursiveProfiler (Story 8.1) and LLMSynthesizer (Story 8.2). It expects the exact same `graph_dict` interface (`nodes`, `edges`, `plugin_results`).
- **Library Choice**: `vis-network` is highly recommended. Load it via CDN: `<script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>`.
- **Portability**: All JSON data must go straight into a `<script>` block in the HTML string: `var nodes = new vis.DataSet({{ nodes_json }});`.
- **Visuals**: Map `depth == 0` (Seed) to a distinct color (e.g., Red/Star), `depth == 1` to Orange, etc. Include standard physics to let the graph "settle" beautifully.

## Dev Agent Record
- **Debug Log**: Không có lỗi đáng kể. vis-network CDN load suôn sẻ. Template dùng `.format()` thay Jinja2 (không cần dependency mới).
- **Completion Notes**: 28/28 unit tests PASSED. HTML được verify thực tế trên browser — star node đỏ (seed), diamond xanh (IP), box xanh lá (DOMAIN), ellipse tím (USERNAME). Edge labels hiển thị tên plugin (Shodan, SearxngOSINT, LeakLookup). UI có controls Fit/Physics và Legend.

## File List
- `[NEW] Core/engine/mindmap_generator.py`
- `[NEW] tests/engine/test_mindmap_generator.py`
- `[MODIFY] demo_story8_2.py` (thêm Phase 3 Mindmap)

## Change Log
- 2026-03-31: Story created and marked ready-for-dev.
- 2026-03-31: Implementation complete — 28 tests pass, HTML verified in browser. Status → review.
