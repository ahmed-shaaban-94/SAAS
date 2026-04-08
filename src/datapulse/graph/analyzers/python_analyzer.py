"""Python code analyzer — uses the built-in ast module for accurate parsing.

Extracts functions, classes, imports, and call relationships.
"""

from __future__ import annotations

import ast
from pathlib import Path

from datapulse.graph import store

# Map src paths to medallion layers
_LAYER_MAP = {
    "bronze": "bronze",
    "pipeline": "bronze",
    "import_pipeline": "bronze",
    "analytics": "gold",
    "forecasting": "gold",
    "ai_light": "gold",
    "targets": "gold",
    "explore": "gold",
    "api": "api",
    "core": "api",
    "cache": "api",
}


def _detect_layer(file_path: str) -> str:
    parts = Path(file_path).parts
    for part in parts:
        if part in _LAYER_MAP:
            return _LAYER_MAP[part]
    return "backend"


def _module_from_path(file_path: str, project_root: str) -> str:
    """Convert file path to Python module path."""
    rel = Path(file_path).relative_to(project_root)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def analyze_file(file_path: str, project_root: str) -> None:
    """Analyze a single Python file."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(content, filename=file_path)
    except (SyntaxError, UnicodeDecodeError):
        return

    rel_path = str(Path(file_path).relative_to(project_root))
    layer = _detect_layer(rel_path)
    module = _module_from_path(file_path, project_root)

    # Pass 1: Register all top-level symbols (functions, classes)
    symbol_ids: dict[str, int] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            sid = store.upsert_symbol(
                name=node.name,
                kind="function",
                file_path=rel_path,
                line_number=node.lineno,
                module=module,
                layer=layer,
            )
            symbol_ids[node.name] = sid

        elif isinstance(node, ast.ClassDef):
            class_id = store.upsert_symbol(
                name=node.name,
                kind="class",
                file_path=rel_path,
                line_number=node.lineno,
                module=module,
                layer=layer,
            )
            symbol_ids[node.name] = class_id

            # Register methods
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    method_name = f"{node.name}.{item.name}"
                    mid = store.upsert_symbol(
                        name=method_name,
                        kind="method",
                        file_path=rel_path,
                        line_number=item.lineno,
                        module=module,
                        layer=layer,
                    )
                    symbol_ids[method_name] = mid

    # Pass 2: Extract imports → create "imports" edges
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("datapulse"):
            for alias in node.names:
                imported_name = alias.name
                existing = store.find_symbol(imported_name)
                if existing:
                    file_sym = store.upsert_symbol(
                        name=Path(rel_path).stem,
                        kind="module",
                        file_path=rel_path,
                        module=module,
                        layer=layer,
                    )
                    store.add_edge(file_sym, existing[0]["id"], "imports")

    # Pass 3: Extract function calls within functions/methods
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            caller_name = node.name
            # Check if it's a method
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in ast.iter_child_nodes(parent):
                        if child is node:
                            caller_name = f"{parent.name}.{node.name}"
                            break

            if caller_name not in symbol_ids:
                continue

            caller_id = symbol_ids[caller_name]

            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    callee = _extract_call_name(child)
                    if callee and callee in symbol_ids:
                        store.add_edge(caller_id, symbol_ids[callee], "calls")
                    elif callee:
                        existing = store.find_symbol(callee)
                        if existing:
                            store.add_edge(caller_id, existing[0]["id"], "calls")


def _extract_call_name(node: ast.Call) -> str | None:
    """Extract the function/method name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
        return node.func.attr
    return None


def analyze_python_project(project_root: str) -> int:
    """Scan all Python files under src/datapulse/."""
    src_dir = Path(project_root) / "src" / "datapulse"
    if not src_dir.exists():
        return 0

    count = 0
    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name.startswith("__"):
            continue
        analyze_file(str(py_file), project_root)
        count += 1

    # Also scan test files for "tests" edges
    test_dir = Path(project_root) / "tests"
    if test_dir.exists():
        for py_file in sorted(test_dir.rglob("test_*.py")):
            _analyze_test_file(str(py_file), project_root)
            count += 1

    return count


def _analyze_test_file(file_path: str, project_root: str) -> None:
    """Extract test → tested-symbol edges from test files."""
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        tree = ast.parse(content, filename=file_path)
    except (SyntaxError, UnicodeDecodeError):
        return

    rel_path = str(Path(file_path).relative_to(project_root))

    # Find what the test file imports from datapulse
    tested_symbols: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("datapulse"):
            for alias in node.names:
                existing = store.find_symbol(alias.name)
                if existing:
                    tested_symbols.append(existing[0]["id"])

    # Register test functions and link them
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            test_id = store.upsert_symbol(
                name=node.name,
                kind="test",
                file_path=rel_path,
                line_number=node.lineno,
                module=rel_path.replace("/", ".").replace(".py", ""),
                layer="test",
            )
            for target_id in tested_symbols:
                store.add_edge(test_id, target_id, "tests")
