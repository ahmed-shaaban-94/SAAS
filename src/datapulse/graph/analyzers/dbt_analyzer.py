"""dbt model analyzer — extracts medallion lineage from SQL + YAML files.

Parses ref(), source() calls and YAML schemas to build the
bronze → silver → gold dependency graph.
"""

from __future__ import annotations

import re
from pathlib import Path

from datapulse.graph import store

# ref('model_name') or ref('package', 'model_name')
_REF_RE = re.compile(r"""\{\{\s*ref\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"][^'"]*['"]\s*)?\)\s*\}\}""")
# source('source_name', 'table_name')
_SOURCE_RE = re.compile(
    r"""\{\{\s*source\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)\s*\}\}"""
)
# Column references in SELECT: table_alias.column_name
_COL_REF_RE = re.compile(r"\b(\w+)\.(\w+)\b")

# Layer detection from path
_LAYER_MAP = {
    "bronze": "bronze",
    "staging": "silver",
    "dims": "gold",
    "facts": "gold",
    "aggs": "gold",
    "features": "gold",
    "marts": "gold",
}


def _detect_layer(file_path: str) -> str:
    """Detect medallion layer from file path."""
    parts = Path(file_path).parts
    for part in reversed(parts):
        if part in _LAYER_MAP:
            return _LAYER_MAP[part]
    return "unknown"


def _model_name(file_path: str) -> str:
    """Extract model name from file path (stem without extension)."""
    return Path(file_path).stem


def analyze_model(file_path: str, content: str, project_root: str) -> None:
    """Analyze a single dbt SQL model file."""
    rel_path = str(Path(file_path).relative_to(project_root))
    model = _model_name(file_path)
    layer = _detect_layer(file_path)

    model_id = store.upsert_symbol(
        name=model,
        kind="dbt_model",
        file_path=rel_path,
        line_number=1,
        module=f"dbt.{layer}",
        layer=layer,
    )

    # Extract ref() dependencies
    for match in _REF_RE.finditer(content):
        dep_name = match.group(1)
        dep_symbols = store.find_symbol(dep_name, kind="dbt_model")
        if dep_symbols:
            dep_id = dep_symbols[0]["id"]
        else:
            dep_layer = _guess_layer(dep_name)
            dep_id = store.upsert_symbol(
                name=dep_name,
                kind="dbt_model",
                file_path=f"dbt/models/{dep_name}.sql",
                module=f"dbt.{dep_layer}",
                layer=dep_layer,
            )
        store.add_edge(model_id, dep_id, "depends_on")

    # Extract source() dependencies
    for match in _SOURCE_RE.finditer(content):
        source_name = match.group(1)
        table_name = match.group(2)
        full_name = f"{source_name}.{table_name}"
        source_symbols = store.find_symbol(full_name, kind="dbt_source")
        if source_symbols:
            source_id = source_symbols[0]["id"]
        else:
            source_id = store.upsert_symbol(
                name=full_name,
                kind="dbt_source",
                file_path=rel_path,
                module="dbt.bronze",
                layer="bronze",
            )
        store.add_edge(model_id, source_id, "depends_on")


def _guess_layer(model_name: str) -> str:
    """Guess layer from model name prefix."""
    if model_name.startswith("stg_"):
        return "silver"
    if model_name.startswith(("dim_", "fct_", "agg_", "feat_", "metrics_")):
        return "gold"
    if model_name.startswith("bronze"):
        return "bronze"
    return "unknown"


def analyze_dbt_project(project_root: str) -> int:
    """Scan all dbt model files and build the lineage graph.

    Two-pass approach:
      Pass 1 — register all models (so every ref target exists)
      Pass 2 — create dependency edges
    """
    dbt_dir = Path(project_root) / "dbt" / "models"
    if not dbt_dir.exists():
        return 0

    sql_files = sorted(dbt_dir.rglob("*.sql"))

    # Pass 1: register all models first
    for sql_file in sql_files:
        rel_path = str(sql_file.relative_to(project_root))
        model = _model_name(str(sql_file))
        layer = _detect_layer(str(sql_file))
        store.upsert_symbol(
            name=model,
            kind="dbt_model",
            file_path=rel_path,
            line_number=1,
            module=f"dbt.{layer}",
            layer=layer,
        )

    # Pass 2: create dependency edges
    for sql_file in sql_files:
        content = sql_file.read_text(encoding="utf-8")
        analyze_model(str(sql_file), content, project_root)

    return len(sql_files)
