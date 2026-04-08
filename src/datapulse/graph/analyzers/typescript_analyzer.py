"""TypeScript/React analyzer — regex-based extraction for Next.js frontend.

Extracts components, hooks, imports, and usage relationships.
"""

from __future__ import annotations

import re
from pathlib import Path

from datapulse.graph import store

# Patterns
_IMPORT_RE = re.compile(
    r"""import\s+(?:\{([^}]+)\}|(\w+))\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_FUNC_COMPONENT_RE = re.compile(
    r"""(?:export\s+(?:default\s+)?)?function\s+(\w+)""",
    re.MULTILINE,
)
_CONST_COMPONENT_RE = re.compile(
    r"""(?:export\s+(?:default\s+)?)?const\s+(\w+)\s*[=:]\s*(?:\([^)]*\)\s*(?::\s*\w+)?\s*=>|React\.FC)""",
    re.MULTILINE,
)
_HOOK_CALL_RE = re.compile(r"""\buse\w+\s*\(""")
_HOOK_DEF_RE = re.compile(
    r"""(?:export\s+(?:default\s+)?)?(?:function|const)\s+(use\w+)""",
    re.MULTILINE,
)
_API_FETCH_RE = re.compile(r"""['"`](/api/[^'"`]+)['"`]""")
_SWR_KEY_RE = re.compile(r"""useSWR\w*\(\s*['"`]?([^'"`),\s]+)""")


def _detect_kind(name: str, file_path: str) -> str:
    if name.startswith("use"):
        return "hook"
    if "/components/" in file_path:
        return "component"
    if "/app/" in file_path and name in ("default", "Page", "Layout"):
        return "page"
    return "component"


def _detect_layer(file_path: str) -> str:
    if "/hooks/" in file_path:
        return "frontend"
    if "/components/charts/" in file_path or "/components/dashboard/" in file_path:
        return "frontend"
    if "/app/(app)/" in file_path:
        return "frontend"
    if "/app/(marketing)/" in file_path:
        return "frontend"
    if "/lib/" in file_path:
        return "frontend"
    return "frontend"


def analyze_file(file_path: str, project_root: str) -> None:
    """Analyze a single TypeScript/TSX file."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return

    rel_path = str(Path(file_path).relative_to(project_root))
    layer = _detect_layer(rel_path)

    # Extract defined symbols
    symbol_ids: dict[str, int] = {}

    # Hook definitions
    for match in _HOOK_DEF_RE.finditer(content):
        name = match.group(1)
        sid = store.upsert_symbol(
            name=name,
            kind="hook",
            file_path=rel_path,
            line_number=content[: match.start()].count("\n") + 1,
            module=rel_path,
            layer=layer,
        )
        symbol_ids[name] = sid

    # Function components
    for match in _FUNC_COMPONENT_RE.finditer(content):
        name = match.group(1)
        if name in symbol_ids or name[0].islower():
            continue
        kind = _detect_kind(name, rel_path)
        sid = store.upsert_symbol(
            name=name,
            kind=kind,
            file_path=rel_path,
            line_number=content[: match.start()].count("\n") + 1,
            module=rel_path,
            layer=layer,
        )
        symbol_ids[name] = sid

    # Const components/hooks
    for match in _CONST_COMPONENT_RE.finditer(content):
        name = match.group(1)
        if name in symbol_ids:
            continue
        kind = _detect_kind(name, rel_path)
        sid = store.upsert_symbol(
            name=name,
            kind=kind,
            file_path=rel_path,
            line_number=content[: match.start()].count("\n") + 1,
            module=rel_path,
            layer=layer,
        )
        symbol_ids[name] = sid

    # Extract imports from project (not node_modules)
    for match in _IMPORT_RE.finditer(content):
        named = match.group(1)
        default = match.group(2)
        source = match.group(3)

        if not source.startswith(("@/", "./", "../", "~/")):
            continue

        imported_names = []
        if named:
            imported_names = [n.strip().split(" as ")[0].strip() for n in named.split(",")]
        if default:
            imported_names.append(default)

        for imp_name in imported_names:
            if not imp_name:
                continue
            existing = store.find_symbol(imp_name)
            if existing:
                for _sym_name, sym_id in symbol_ids.items():
                    store.add_edge(sym_id, existing[0]["id"], "imports")

    # Extract API endpoint references → link frontend to API layer
    for match in _API_FETCH_RE.finditer(content):
        endpoint = match.group(1)
        ep_id = store.upsert_symbol(
            name=endpoint,
            kind="api_endpoint",
            file_path=rel_path,
            module="api",
            layer="api",
        )
        for sym_id in symbol_ids.values():
            store.add_edge(sym_id, ep_id, "calls")

    # Extract SWR keys (which are often API paths)
    for match in _SWR_KEY_RE.finditer(content):
        key = match.group(1)
        if key.startswith("/"):
            ep_id = store.upsert_symbol(
                name=key,
                kind="api_endpoint",
                file_path=rel_path,
                module="api",
                layer="api",
            )
            for sym_id in symbol_ids.values():
                store.add_edge(sym_id, ep_id, "calls")


def analyze_frontend_project(project_root: str) -> int:
    """Scan all TypeScript/TSX files under frontend/src/."""
    frontend_dir = Path(project_root) / "frontend" / "src"
    if not frontend_dir.exists():
        return 0

    count = 0
    for ts_file in sorted(frontend_dir.rglob("*.ts")):
        if "node_modules" in str(ts_file) or ".next" in str(ts_file):
            continue
        analyze_file(str(ts_file), project_root)
        count += 1
    for tsx_file in sorted(frontend_dir.rglob("*.tsx")):
        if "node_modules" in str(tsx_file) or ".next" in str(tsx_file):
            continue
        analyze_file(str(tsx_file), project_root)
        count += 1

    return count
