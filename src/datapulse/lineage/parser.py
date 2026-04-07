"""Parse dbt SQL files to extract model lineage via ref() calls."""

from __future__ import annotations

import re
from pathlib import Path

from datapulse.lineage.models import LineageEdge, LineageGraph, LineageNode
from datapulse.logging import get_logger

log = get_logger(__name__)

_REF_PATTERN = re.compile(r"""\{\{\s*ref\(\s*['"](\w+)['"]\s*\)\s*\}\}""")

# Default dbt models directory
_DBT_DIR = Path(__file__).resolve().parents[3] / "dbt" / "models"


def _classify_model(name: str) -> tuple[str, str]:
    """Classify a model by name prefix into (layer, model_type)."""
    if name.startswith("stg_"):
        return "silver", "staging"
    if name.startswith("dim_"):
        return "silver", "dimension"
    if name.startswith("fct_"):
        return "gold", "fact"
    if name.startswith("agg_"):
        return "gold", "aggregate"
    if name.startswith("feat_"):
        return "gold", "feature"
    if name.startswith("metrics_") or name.startswith("seed_"):
        return "gold", "aggregate"
    return "bronze", "source"


def parse_lineage(dbt_dir: Path | None = None) -> LineageGraph:
    """Scan all .sql files under dbt_dir for ref() calls and build a lineage graph."""
    base = dbt_dir or _DBT_DIR
    if not base.exists():
        log.warning("dbt_dir_not_found", path=str(base))
        return LineageGraph(nodes=[], edges=[])

    nodes_map: dict[str, LineageNode] = {}
    edges: list[LineageEdge] = []

    for sql_file in sorted(base.rglob("*.sql")):
        model_name = sql_file.stem
        layer, model_type = _classify_model(model_name)
        nodes_map[model_name] = LineageNode(name=model_name, layer=layer, model_type=model_type)

        content = sql_file.read_text(encoding="utf-8", errors="ignore")
        for match in _REF_PATTERN.finditer(content):
            upstream = match.group(1)
            # Ensure upstream node exists
            if upstream not in nodes_map:
                up_layer, up_type = _classify_model(upstream)
                nodes_map[upstream] = LineageNode(name=upstream, layer=up_layer, model_type=up_type)
            edges.append(LineageEdge(source=upstream, target=model_name))

    return LineageGraph(
        nodes=list(nodes_map.values()),
        edges=edges,
    )


def get_model_lineage(model_name: str, dbt_dir: Path | None = None) -> LineageGraph:
    """Get upstream and downstream lineage for a specific model."""
    full = parse_lineage(dbt_dir)

    # Collect upstream and downstream via BFS
    related: set[str] = {model_name}
    # upstream
    queue = [model_name]
    while queue:
        current = queue.pop(0)
        for e in full.edges:
            if e.target == current and e.source not in related:
                related.add(e.source)
                queue.append(e.source)
    # downstream
    queue = [model_name]
    visited_down: set[str] = {model_name}
    while queue:
        current = queue.pop(0)
        for e in full.edges:
            if e.source == current and e.target not in visited_down:
                related.add(e.target)
                visited_down.add(e.target)
                queue.append(e.target)

    filtered_nodes = [n for n in full.nodes if n.name in related]
    filtered_edges = [e for e in full.edges if e.source in related and e.target in related]

    return LineageGraph(nodes=filtered_nodes, edges=filtered_edges)
