"""Tests for datapulse.graph — store, analyzers, indexer, and MCP tools."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datapulse.graph import store
from datapulse.graph.analyzers import dbt_analyzer, python_analyzer, typescript_analyzer
from datapulse.graph.indexer import index


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use a temporary database for each test."""
    db_path = tmp_path / "test_graph.db"
    monkeypatch.setattr(store, "DB_PATH", db_path)
    store.init_db()
    yield
    if db_path.exists():
        db_path.unlink()


# ── store.py ──────────────────────────────────────────────────────


class TestStore:
    def test_init_db_creates_tables(self):
        s = store.stats()
        assert s["total_symbols"] == 0
        assert s["total_edges"] == 0

    def test_upsert_symbol_and_find(self):
        sid = store.upsert_symbol(
            name="my_func",
            kind="function",
            file_path="a.py",
            line_number=10,
            module="mod",
            layer="gold",
        )
        assert sid > 0
        results = store.find_symbol("my_func")
        assert len(results) == 1
        assert results[0]["name"] == "my_func"
        assert results[0]["layer"] == "gold"

    def test_upsert_symbol_idempotent(self):
        id1 = store.upsert_symbol(name="f", kind="function", file_path="a.py")
        id2 = store.upsert_symbol(name="f", kind="function", file_path="a.py")
        assert id1 == id2

    def test_add_edge_and_retrieve(self):
        s1 = store.upsert_symbol(name="caller", kind="function", file_path="a.py")
        s2 = store.upsert_symbol(name="callee", kind="function", file_path="b.py")
        store.add_edge(s1, s2, "calls")

        outgoing = store.get_edges_from(s1)
        assert len(outgoing) == 1
        assert outgoing[0]["name"] == "callee"

        incoming = store.get_edges_to(s2)
        assert len(incoming) == 1
        assert incoming[0]["name"] == "caller"

    def test_find_symbol_with_kind_filter(self):
        store.upsert_symbol(name="X", kind="function", file_path="a.py")
        store.upsert_symbol(name="X", kind="class", file_path="b.py")
        funcs = store.find_symbol("X", kind="function")
        assert len(funcs) == 1
        assert funcs[0]["kind"] == "function"

    def test_find_by_file(self):
        store.upsert_symbol(name="a", kind="function", file_path="x.py")
        store.upsert_symbol(name="b", kind="function", file_path="x.py", line_number=20)
        store.upsert_symbol(name="c", kind="function", file_path="y.py")
        results = store.find_by_file("x.py")
        assert len(results) == 2

    def test_clear(self):
        store.upsert_symbol(name="f", kind="function", file_path="a.py")
        store.clear()
        assert store.stats()["total_symbols"] == 0

    def test_search_query_with_filters(self):
        store.upsert_symbol(name="get_revenue", kind="function", file_path="a.py", layer="gold")
        store.upsert_symbol(name="get_revenue", kind="method", file_path="b.py", layer="api")
        results = store.search_query("revenue", kind="function")
        assert len(results) == 1
        results = store.search_query("revenue", layer="api")
        assert len(results) == 1

    def test_get_symbol_by_id(self):
        sid = store.upsert_symbol(name="f", kind="function", file_path="a.py")
        sym = store.get_symbol_by_id(sid)
        assert sym is not None
        assert sym["name"] == "f"
        assert store.get_symbol_by_id(99999) is None

    def test_context_query_not_found(self):
        result = store.context_query("nonexistent")
        assert "error" in result

    def test_context_query_full(self):
        s1 = store.upsert_symbol(name="target", kind="function", file_path="a.py", layer="gold")
        s2 = store.upsert_symbol(name="caller", kind="function", file_path="b.py", layer="api")
        s3 = store.upsert_symbol(name="test_target", kind="test", file_path="t.py", layer="test")
        store.add_edge(s2, s1, "calls")
        store.add_edge(s3, s1, "tests")

        ctx = store.context_query("target")
        assert ctx["symbol"] == "target"
        assert ctx["layer"] == "gold"
        assert len(ctx["callers"]) == 1
        assert len(ctx["tested_by"]) == 1

    def test_impact_query_bfs(self):
        a = store.upsert_symbol(
            name="bronze_tbl",
            kind="dbt_model",
            file_path="a.sql",
            layer="bronze",
        )
        b = store.upsert_symbol(
            name="stg_tbl",
            kind="dbt_model",
            file_path="b.sql",
            layer="silver",
        )
        c = store.upsert_symbol(
            name="fct_tbl",
            kind="dbt_model",
            file_path="c.sql",
            layer="gold",
        )
        store.add_edge(b, a, "depends_on")
        store.add_edge(c, b, "depends_on")

        result = store.impact_query("bronze_tbl", max_depth=3)
        assert 1 in result
        names = [h["name"] for d in result.values() for h in d]
        assert "stg_tbl" in names

    def test_impact_query_not_found(self):
        result = store.impact_query("nonexistent")
        assert result == {}

    def test_stats(self):
        store.upsert_symbol(name="a", kind="function", file_path="a.py", layer="gold")
        store.upsert_symbol(name="b", kind="class", file_path="b.py", layer="api")
        s = store.stats()
        assert s["total_symbols"] == 2
        assert s["by_layer"]["gold"] == 1
        assert s["by_kind"]["function"] == 1


# ── dbt_analyzer.py ──────────────────────────────────────────────


class TestDbtAnalyzer:
    def test_detect_layer(self):
        assert dbt_analyzer._detect_layer("/dbt/models/bronze/x.sql") == "bronze"
        assert dbt_analyzer._detect_layer("/dbt/models/staging/x.sql") == "silver"
        assert dbt_analyzer._detect_layer("/dbt/models/marts/dims/x.sql") == "gold"
        assert dbt_analyzer._detect_layer("/dbt/models/marts/facts/x.sql") == "gold"
        assert dbt_analyzer._detect_layer("/dbt/models/marts/aggs/x.sql") == "gold"
        assert dbt_analyzer._detect_layer("/other/x.sql") == "unknown"

    def test_guess_layer(self):
        assert dbt_analyzer._guess_layer("stg_sales") == "silver"
        assert dbt_analyzer._guess_layer("dim_customer") == "gold"
        assert dbt_analyzer._guess_layer("fct_sales") == "gold"
        assert dbt_analyzer._guess_layer("agg_revenue") == "gold"
        assert dbt_analyzer._guess_layer("bronze_raw") == "bronze"
        assert dbt_analyzer._guess_layer("random") == "unknown"

    def test_analyze_model_ref(self, tmp_path: Path):
        # Pre-register the dependency
        store.upsert_symbol(
            name="stg_sales",
            kind="dbt_model",
            file_path="dbt/models/staging/stg_sales.sql",
            layer="silver",
        )
        sql = "SELECT * FROM {{ ref('stg_sales') }}"
        model_file = tmp_path / "dbt" / "models" / "marts" / "facts" / "fct_sales.sql"
        model_file.parent.mkdir(parents=True)
        model_file.write_text(sql)
        dbt_analyzer.analyze_model(str(model_file), sql, str(tmp_path))

        fct = store.find_symbol("fct_sales", kind="dbt_model")
        assert len(fct) == 1
        assert fct[0]["layer"] == "gold"
        edges = store.get_edges_from(fct[0]["id"])
        assert any(e["name"] == "stg_sales" for e in edges)

    def test_analyze_model_source(self, tmp_path: Path):
        sql = "SELECT * FROM {{ source('bronze', 'sales') }}"
        model_file = tmp_path / "dbt" / "models" / "bronze" / "bronze_sales.sql"
        model_file.parent.mkdir(parents=True)
        model_file.write_text(sql)
        dbt_analyzer.analyze_model(str(model_file), sql, str(tmp_path))

        src = store.find_symbol("bronze.sales", kind="dbt_source")
        assert len(src) == 1

    def test_analyze_dbt_project(self, tmp_path: Path):
        models_dir = tmp_path / "dbt" / "models"
        (models_dir / "staging").mkdir(parents=True)
        (models_dir / "staging" / "stg_x.sql").write_text("SELECT 1")
        (models_dir / "marts" / "facts").mkdir(parents=True)
        (models_dir / "marts" / "facts" / "fct_x.sql").write_text(
            "SELECT * FROM {{ ref('stg_x') }}"
        )
        count = dbt_analyzer.analyze_dbt_project(str(tmp_path))
        assert count == 2

    def test_analyze_dbt_project_no_dir(self, tmp_path: Path):
        assert dbt_analyzer.analyze_dbt_project(str(tmp_path)) == 0


# ── python_analyzer.py ───────────────────────────────────────────


class TestPythonAnalyzer:
    def test_analyze_file_functions_and_classes(self, tmp_path: Path):
        src = tmp_path / "src" / "datapulse" / "analytics"
        src.mkdir(parents=True)
        code = """
class MyService:
    def get_data(self):
        pass

def helper():
    pass
"""
        (src / "service.py").write_text(code)
        python_analyzer.analyze_file(str(src / "service.py"), str(tmp_path))

        classes = store.find_symbol("MyService", kind="class")
        assert len(classes) == 1
        funcs = store.find_symbol("helper", kind="function")
        assert len(funcs) == 1
        methods = store.find_symbol("MyService.get_data", kind="method")
        assert len(methods) == 1

    def test_analyze_file_syntax_error(self, tmp_path: Path):
        src = tmp_path / "src" / "datapulse"
        src.mkdir(parents=True)
        (src / "bad.py").write_text("def broken(:\n")
        # Should not raise
        python_analyzer.analyze_file(str(src / "bad.py"), str(tmp_path))

    def test_analyze_python_project(self, tmp_path: Path):
        src = tmp_path / "src" / "datapulse"
        src.mkdir(parents=True)
        (src / "mod.py").write_text("def foo(): pass")
        count = python_analyzer.analyze_python_project(str(tmp_path))
        assert count >= 1

    def test_analyze_python_project_no_dir(self, tmp_path: Path):
        assert python_analyzer.analyze_python_project(str(tmp_path)) == 0

    def test_detect_layer(self):
        assert python_analyzer._detect_layer("src/datapulse/bronze/loader.py") == "bronze"
        assert python_analyzer._detect_layer("src/datapulse/analytics/service.py") == "gold"
        assert python_analyzer._detect_layer("src/datapulse/api/routes/health.py") == "api"
        assert python_analyzer._detect_layer("src/datapulse/other.py") == "backend"

    def test_analyze_test_file(self, tmp_path: Path):
        # First create a symbol to be tested
        store.upsert_symbol(name="MyFunc", kind="function", file_path="src/datapulse/a.py")

        tests = tmp_path / "tests"
        tests.mkdir()
        code = """
from datapulse.a import MyFunc

def test_my_func():
    pass
"""
        (tests / "test_a.py").write_text(code)
        python_analyzer._analyze_test_file(str(tests / "test_a.py"), str(tmp_path))

        test_syms = store.find_symbol("test_my_func", kind="test")
        assert len(test_syms) == 1


# ── typescript_analyzer.py ───────────────────────────────────────


class TestTypescriptAnalyzer:
    def test_analyze_hook(self, tmp_path: Path):
        frontend = tmp_path / "frontend" / "src" / "hooks"
        frontend.mkdir(parents=True)
        code = 'export function useRevenue() { return useSWR("/api/v1/revenue") }'
        (frontend / "use-revenue.ts").write_text(code)
        typescript_analyzer.analyze_file(str(frontend / "use-revenue.ts"), str(tmp_path))

        hooks = store.find_symbol("useRevenue", kind="hook")
        assert len(hooks) == 1

    def test_analyze_component(self, tmp_path: Path):
        frontend = tmp_path / "frontend" / "src" / "components"
        frontend.mkdir(parents=True)
        code = "export function ChartCard({ children }) { return <div>{children}</div> }"
        (frontend / "chart-card.tsx").write_text(code)
        typescript_analyzer.analyze_file(str(frontend / "chart-card.tsx"), str(tmp_path))

        comps = store.find_symbol("ChartCard", kind="component")
        assert len(comps) == 1

    def test_analyze_api_endpoint_extraction(self, tmp_path: Path):
        frontend = tmp_path / "frontend" / "src" / "hooks"
        frontend.mkdir(parents=True)
        code = """
export function useData() {
  return useSWR("/api/v1/analytics/summary")
}
"""
        (frontend / "use-data.ts").write_text(code)
        typescript_analyzer.analyze_file(str(frontend / "use-data.ts"), str(tmp_path))

        endpoints = store.find_symbol("/api/v1/analytics/summary", kind="api_endpoint")
        assert len(endpoints) == 1

    def test_analyze_frontend_project(self, tmp_path: Path):
        frontend = tmp_path / "frontend" / "src"
        frontend.mkdir(parents=True)
        (frontend / "app.ts").write_text("export function App() {}")
        count = typescript_analyzer.analyze_frontend_project(str(tmp_path))
        assert count >= 1

    def test_analyze_frontend_project_no_dir(self, tmp_path: Path):
        assert typescript_analyzer.analyze_frontend_project(str(tmp_path)) == 0


# ── indexer.py ───────────────────────────────────────────────────


class TestIndexer:
    def test_index_empty_project(self, tmp_path: Path):
        result = index(str(tmp_path))
        assert result["files_indexed"]["total"] == 0
        assert result["elapsed_seconds"] >= 0

    def test_index_with_dbt(self, tmp_path: Path):
        models = tmp_path / "dbt" / "models" / "staging"
        models.mkdir(parents=True)
        (models / "stg_test.sql").write_text("SELECT 1")
        result = index(str(tmp_path))
        assert result["files_indexed"]["dbt_models"] == 1


# ── mcp_server.py ────────────────────────────────────────────────


class TestMCPTools:
    def _setup_graph(self):
        a = store.upsert_symbol(
            name="bronze_sales",
            kind="dbt_model",
            file_path="dbt/models/bronze/bronze_sales.sql",
            layer="bronze",
        )
        b = store.upsert_symbol(
            name="stg_sales",
            kind="dbt_model",
            file_path="dbt/models/staging/stg_sales.sql",
            layer="silver",
        )
        c = store.upsert_symbol(
            name="fct_sales",
            kind="dbt_model",
            file_path="dbt/models/marts/facts/fct_sales.sql",
            layer="gold",
        )
        store.add_edge(b, a, "depends_on")
        store.add_edge(c, b, "depends_on")

    def test_dp_impact(self):
        from datapulse.graph.mcp_server import dp_impact

        self._setup_graph()
        result = json.loads(dp_impact("bronze_sales", max_depth=2))
        assert result["total_affected"] > 0
        assert "by_depth" in result

    def test_dp_impact_not_found(self):
        from datapulse.graph.mcp_server import dp_impact

        result = json.loads(dp_impact("nonexistent_symbol"))
        assert "error" in result

    def test_dp_context(self):
        from datapulse.graph.mcp_server import dp_context

        self._setup_graph()
        result = json.loads(dp_context("stg_sales"))
        assert result["symbol"] == "stg_sales"
        assert result["layer"] == "silver"

    def test_dp_query(self):
        from datapulse.graph.mcp_server import dp_query

        self._setup_graph()
        result = json.loads(dp_query("sales"))
        assert result["count"] == 3

    def test_dp_query_with_filters(self):
        from datapulse.graph.mcp_server import dp_query

        self._setup_graph()
        result = json.loads(dp_query("sales", layer="gold"))
        assert result["count"] == 1

    def test_dp_query_no_results(self):
        from datapulse.graph.mcp_server import dp_query

        result = json.loads(dp_query("zzzzz_nonexistent"))
        assert result["results"] == []

    def test_dp_detect_changes(self):
        from datapulse.graph.mcp_server import dp_detect_changes

        self._setup_graph()
        result = json.loads(dp_detect_changes())
        assert "changed_files" in result

    def test_risk_summary(self):
        from datapulse.graph.mcp_server import _risk_summary

        high = [
            {"layer": "bronze", "downstream_affected": 15},
            {"layer": "silver", "downstream_affected": 5},
            {"layer": "gold", "downstream_affected": 3},
        ]
        assert "HIGH" in _risk_summary(high)

        medium = [
            {"layer": "gold", "downstream_affected": 7},
            {"layer": "api", "downstream_affected": 2},
        ]
        assert "MEDIUM" in _risk_summary(medium)

        low = [{"layer": "gold", "downstream_affected": 2}]
        assert "LOW" in _risk_summary(low)
