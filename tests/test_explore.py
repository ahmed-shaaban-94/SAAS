"""Comprehensive tests for the explore module.

Covers:
- models.py: enums, Pydantic models, defaults
- manifest_parser.py: type inference, label conversion, YAML parsing, catalog building
- sql_builder.py: SQL generation, validation, filters, joins
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from datapulse.explore.manifest_parser import (
    _col_to_label,
    _infer_dimension_type,
    _parse_model_yaml,
    build_catalog,
    parse_dbt_yaml,
)
from datapulse.explore.models import (
    Dimension,
    DimensionType,
    ExploreCatalog,
    ExploreFilter,
    ExploreModel,
    ExploreQuery,
    ExploreResult,
    JoinPath,
    Metric,
    MetricType,
    SortDirection,
    SortSpec,
)
from datapulse.explore.sql_builder import build_sql

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_dimension(
    name: str = "customer_name",
    label: str = "Customer Name",
    model: str = "fct_sales",
    dim_type: DimensionType = DimensionType.string,
) -> Dimension:
    return Dimension(name=name, label=label, model=model, dimension_type=dim_type)


def _make_metric(
    name: str = "total_sales",
    label: str = "Total Sales",
    model: str = "fct_sales",
    column: str = "net_sales",
    metric_type: MetricType = MetricType.sum,
) -> Metric:
    return Metric(
        name=name,
        label=label,
        model=model,
        column=column,
        metric_type=metric_type,
    )


def _make_explore_model(
    name: str = "fct_sales",
    dimensions: list[Dimension] | None = None,
    metrics: list[Metric] | None = None,
    joins: list[JoinPath] | None = None,
    schema_name: str = "public_marts",
) -> ExploreModel:
    return ExploreModel(
        name=name,
        label="Fact Sales",
        schema_name=schema_name,
        dimensions=dimensions or [],
        metrics=metrics or [],
        joins=joins or [],
    )


def _make_catalog(models: list[ExploreModel] | None = None) -> ExploreCatalog:
    return ExploreCatalog(models=models or [])


def _simple_catalog() -> ExploreCatalog:
    """A small catalog with one model containing one dim and one metric."""
    dim = _make_dimension()
    metric = _make_metric()
    model = _make_explore_model(dimensions=[dim], metrics=[metric])
    return _make_catalog([model])


# ------------------------------------------------------------------
# 1-9: models.py
# ------------------------------------------------------------------


class TestDimensionType:
    def test_values(self):
        assert DimensionType.string == "string"
        assert DimensionType.number == "number"
        assert DimensionType.date == "date"
        assert DimensionType.boolean == "boolean"

    def test_membership(self):
        assert len(DimensionType) == 4


class TestMetricType:
    def test_values(self):
        assert MetricType.sum == "sum"
        assert MetricType.average == "average"
        assert MetricType.count == "count"
        assert MetricType.count_distinct == "count_distinct"
        assert MetricType.min == "min"
        assert MetricType.max == "max"

    def test_membership(self):
        assert len(MetricType) == 6


class TestDimension:
    def test_creation_all_fields(self):
        dim = Dimension(
            name="brand",
            label="Brand",
            description="Product brand",
            dimension_type=DimensionType.string,
            model="dim_product",
        )
        assert dim.name == "brand"
        assert dim.label == "Brand"
        assert dim.description == "Product brand"
        assert dim.dimension_type == DimensionType.string
        assert dim.model == "dim_product"

    def test_default_description(self):
        dim = _make_dimension()
        assert dim.description == ""

    def test_default_dimension_type(self):
        dim = Dimension(name="x", label="X", model="m")
        assert dim.dimension_type == DimensionType.string


class TestMetric:
    def test_creation_all_fields(self):
        m = Metric(
            name="avg_quantity",
            label="Avg Quantity",
            description="Average order quantity",
            metric_type=MetricType.average,
            column="quantity",
            model="fct_sales",
        )
        assert m.name == "avg_quantity"
        assert m.label == "Avg Quantity"
        assert m.description == "Average order quantity"
        assert m.metric_type == MetricType.average
        assert m.column == "quantity"
        assert m.model == "fct_sales"


class TestJoinPath:
    def test_creation(self):
        jp = JoinPath(
            join_model="dim_customer",
            sql_on="${fct_sales.customer_key} = ${dim_customer.customer_key}",
        )
        assert jp.join_model == "dim_customer"
        assert "${fct_sales.customer_key}" in jp.sql_on


class TestExploreModel:
    def test_defaults(self):
        model = ExploreModel(name="fct_sales")
        assert model.name == "fct_sales"
        assert model.label == ""
        assert model.description == ""
        assert model.schema_name == "public_marts"
        assert model.dimensions == []
        assert model.metrics == []
        assert model.joins == []


class TestExploreQuery:
    def test_defaults(self):
        q = ExploreQuery(model="fct_sales")
        assert q.model == "fct_sales"
        assert q.dimensions == []
        assert q.metrics == []
        assert q.filters == []
        assert q.sorts == []
        assert q.limit == 500


class TestExploreFilter:
    def test_operator_default(self):
        f = ExploreFilter(field="brand", value="Aspirin")
        assert f.operator == "eq"

    def test_explicit_operator(self):
        f = ExploreFilter(field="net_sales", operator="gt", value=100)
        assert f.operator == "gt"


class TestExploreResult:
    def test_defaults(self):
        r = ExploreResult()
        assert r.columns == []
        assert r.rows == []
        assert r.row_count == 0
        assert r.sql == ""
        assert r.truncated is False


class TestSortDirection:
    def test_values(self):
        assert SortDirection.asc == "asc"
        assert SortDirection.desc == "desc"


# ------------------------------------------------------------------
# 10-15: manifest_parser.py
# ------------------------------------------------------------------


class TestInferDimensionType:
    @pytest.mark.parametrize(
        "col,expected",
        [
            ("is_returned", DimensionType.boolean),
            ("has_discount", DimensionType.boolean),
            ("date", DimensionType.date),
            ("created_at", DimensionType.date),
            ("year_month", DimensionType.date),
            ("quantity", DimensionType.number),
            ("net_sales", DimensionType.number),
            ("discount_rate", DimensionType.number),
            ("customer_key", DimensionType.number),
            ("product_key", DimensionType.number),
            ("brand", DimensionType.string),
            ("customer_name", DimensionType.string),
        ],
    )
    def test_infer(self, col, expected):
        assert _infer_dimension_type(col) == expected


class TestColToLabel:
    @pytest.mark.parametrize(
        "col,expected",
        [
            ("customer_name", "Customer Name"),
            ("net_sales", "Net Sales"),
            ("id", "Id"),
            ("year_month", "Year Month"),
        ],
    )
    def test_conversion(self, col, expected):
        assert _col_to_label(col) == expected


class TestParseModelYaml:
    def test_basic(self):
        model_dict = {
            "name": "fct_sales",
            "description": "Sales fact table",
            "meta": {
                "label": "Sales",
                "joins": [
                    {
                        "join": "dim_customer",
                        "sql_on": "${fct_sales.ck} = ${dim_customer.ck}",
                    }
                ],
            },
            "columns": [
                {
                    "name": "customer_name",
                    "description": "Name of customer",
                },
                {
                    "name": "net_sales",
                    "description": "Net sales amount",
                    "meta": {
                        "metrics": {
                            "total_sales": {"type": "sum"},
                        },
                    },
                },
            ],
        }
        result = _parse_model_yaml(model_dict)
        assert result.name == "fct_sales"
        assert result.label == "Sales"
        assert result.description == "Sales fact table"
        assert result.schema_name == "public_marts"
        assert len(result.dimensions) == 2
        assert len(result.metrics) == 1
        assert result.metrics[0].name == "total_sales"
        assert result.metrics[0].metric_type == MetricType.sum
        assert len(result.joins) == 1
        assert result.joins[0].join_model == "dim_customer"

    def test_skips_internal_columns(self):
        model_dict = {
            "name": "fct_sales",
            "columns": [
                {"name": "tenant_id"},
                {"name": "sales_key"},
                {"name": "brand"},
            ],
        }
        result = _parse_model_yaml(model_dict)
        assert len(result.dimensions) == 1
        assert result.dimensions[0].name == "brand"

    def test_explicit_dimension_type_in_meta(self):
        model_dict = {
            "name": "fct_sales",
            "columns": [
                {
                    "name": "brand",
                    "meta": {"dimension_type": "string"},
                },
            ],
        }
        result = _parse_model_yaml(model_dict)
        assert result.dimensions[0].dimension_type == DimensionType.string

    def test_invalid_metric_type_falls_back_to_sum(self):
        model_dict = {
            "name": "fct_sales",
            "columns": [
                {
                    "name": "amount",
                    "meta": {
                        "metrics": {
                            "weird_metric": {"type": "median"},
                        },
                    },
                },
            ],
        }
        result = _parse_model_yaml(model_dict)
        assert result.metrics[0].metric_type == MetricType.sum


class TestParseDbtYaml:
    def test_reads_yaml_file(self, tmp_path: Path):
        yaml_data = {
            "models": [
                {
                    "name": "fct_sales",
                    "columns": [{"name": "brand"}],
                }
            ]
        }
        yaml_file = tmp_path / "_test__models.yml"
        yaml_file.write_text(yaml.dump(yaml_data))

        result = parse_dbt_yaml(yaml_file)
        assert len(result) == 1
        assert result[0].name == "fct_sales"

    def test_returns_empty_for_no_models_key(self, tmp_path: Path):
        yaml_data = {"sources": [{"name": "raw"}]}
        yaml_file = tmp_path / "_test__sources.yml"
        yaml_file.write_text(yaml.dump(yaml_data))

        result = parse_dbt_yaml(yaml_file)
        assert result == []

    def test_returns_empty_for_empty_file(self, tmp_path: Path):
        yaml_file = tmp_path / "_test__models.yml"
        yaml_file.write_text("")

        result = parse_dbt_yaml(yaml_file)
        assert result == []


class TestBuildCatalog:
    def test_scans_marts_directory(self, tmp_path: Path):
        # Create dbt models/marts/aggs/ structure
        aggs_dir = tmp_path / "marts" / "aggs"
        aggs_dir.mkdir(parents=True)

        yaml_data = {
            "models": [
                {
                    "name": "agg_sales_daily",
                    "columns": [
                        {"name": "date"},
                        {
                            "name": "net_sales",
                            "meta": {
                                "metrics": {
                                    "total_sales": {"type": "sum"},
                                }
                            },
                        },
                    ],
                }
            ]
        }
        (aggs_dir / "_aggs__models.yml").write_text(yaml.dump(yaml_data))

        catalog = build_catalog(tmp_path)
        assert len(catalog.models) == 1
        assert catalog.models[0].name == "agg_sales_daily"

    def test_returns_empty_when_marts_missing(self, tmp_path: Path):
        catalog = build_catalog(tmp_path)
        assert catalog.models == []


# ------------------------------------------------------------------
# 16-25: sql_builder.py
# ------------------------------------------------------------------


class TestBuildSql:
    def test_dimensions_only(self):
        dim = _make_dimension(name="brand", label="Brand")
        model = _make_explore_model(dimensions=[dim])
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales", dimensions=["brand"])

        sql, params = build_sql(query, catalog)
        assert "SELECT fct_sales.brand" in sql
        assert "FROM public_marts.fct_sales AS fct_sales" in sql
        assert "GROUP BY" not in sql
        assert "LIMIT 500" in sql
        assert params == {}

    def test_metrics_only(self):
        metric = _make_metric()
        model = _make_explore_model(metrics=[metric])
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales", metrics=["total_sales"])

        sql, params = build_sql(query, catalog)
        assert "SUM(fct_sales.net_sales) AS total_sales" in sql
        assert "GROUP BY" not in sql

    def test_dims_and_metrics_group_by(self):
        dim = _make_dimension(name="brand", label="Brand")
        metric = _make_metric()
        model = _make_explore_model(dimensions=[dim], metrics=[metric])
        catalog = _make_catalog([model])
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["brand"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)
        assert "SELECT fct_sales.brand" in sql
        assert "SUM(fct_sales.net_sales) AS total_sales" in sql
        assert "GROUP BY fct_sales.brand" in sql

    def test_unknown_model_raises(self):
        catalog = _make_catalog([])
        query = ExploreQuery(model="nonexistent", dimensions=["x"])

        with pytest.raises(ValueError, match="Unknown model 'nonexistent'"):
            build_sql(query, catalog)

    def test_unknown_dimension_raises(self):
        dim = _make_dimension(name="brand", label="Brand")
        model = _make_explore_model(dimensions=[dim])
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales", dimensions=["unknown_col"])

        with pytest.raises(ValueError, match="Unknown dimension 'unknown_col'"):
            build_sql(query, catalog)

    def test_unknown_metric_raises(self):
        dim = _make_dimension(name="brand", label="Brand")
        model = _make_explore_model(dimensions=[dim])
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales", dimensions=["brand"], metrics=["bad_metric"])

        with pytest.raises(ValueError, match="Unknown metric 'bad_metric'"):
            build_sql(query, catalog)

    def test_filter_eq(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            filters=[ExploreFilter(field="customer_name", value="Acme")],
        )

        sql, params = build_sql(query, catalog)
        assert "fct_sales.customer_name = :p0" in sql
        assert params["p0"] == "Acme"

    def test_filter_gt(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            filters=[ExploreFilter(field="customer_name", operator="gt", value=100)],
        )

        sql, params = build_sql(query, catalog)
        assert "fct_sales.customer_name > :p0" in sql
        assert params["p0"] == 100

    def test_filter_like(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            filters=[ExploreFilter(field="customer_name", operator="like", value="%pharma%")],
        )

        sql, params = build_sql(query, catalog)
        assert "fct_sales.customer_name ILIKE :p0" in sql
        assert params["p0"] == "%pharma%"

    def test_filter_in_list(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            filters=[
                ExploreFilter(
                    field="customer_name",
                    operator="in",
                    value=["Acme", "Beta"],
                )
            ],
        )

        sql, params = build_sql(query, catalog)
        assert "fct_sales.customer_name IN (:p0_0, :p0_1)" in sql
        assert params["p0_0"] == "Acme"
        assert params["p0_1"] == "Beta"

    def test_unsafe_identifier_raises(self):
        dim = _make_dimension(name="brand", label="Brand")
        model = _make_explore_model(dimensions=[dim], schema_name="DROP TABLE")
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales", dimensions=["brand"])

        with pytest.raises(ValueError, match="Unsafe schema name"):
            build_sql(query, catalog)

    def test_unsafe_filter_field_raises(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            filters=[ExploreFilter(field="1; DROP TABLE", operator="eq", value="x")],
        )

        with pytest.raises(ValueError, match="Unsafe filter field"):
            build_sql(query, catalog)

    def test_join_clauses_included(self):
        base_dim = _make_dimension(name="customer_key", label="CK", dim_type=DimensionType.number)
        base_metric = _make_metric()
        join_dim = _make_dimension(
            name="customer_name",
            label="Customer Name",
            model="dim_customer",
        )
        join_model = _make_explore_model(name="dim_customer", dimensions=[join_dim])
        base_model = _make_explore_model(
            dimensions=[base_dim],
            metrics=[base_metric],
            joins=[
                JoinPath(
                    join_model="dim_customer",
                    sql_on=("${fct_sales.customer_key} = ${dim_customer.customer_key}"),
                )
            ],
        )
        catalog = _make_catalog([base_model, join_model])
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)
        assert "LEFT JOIN public_marts.dim_customer" in sql
        assert "dim_customer.customer_name" in sql

    def test_no_dim_no_metric_raises(self):
        model = _make_explore_model()
        catalog = _make_catalog([model])
        query = ExploreQuery(model="fct_sales")

        with pytest.raises(ValueError, match="At least one dimension or metric"):
            build_sql(query, catalog)

    def test_sort_spec_applied(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
            sorts=[SortSpec(field="total_sales", direction=SortDirection.asc)],
        )

        sql, _ = build_sql(query, catalog)
        assert "ORDER BY total_sales asc" in sql

    def test_default_sort_by_first_metric(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
        )

        sql, _ = build_sql(query, catalog)
        assert "ORDER BY total_sales DESC" in sql

    def test_custom_limit(self):
        catalog = _simple_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            limit=100,
        )

        sql, _ = build_sql(query, catalog)
        assert "LIMIT 100" in sql
