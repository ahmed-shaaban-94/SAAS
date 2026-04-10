"""Tests for the explore SQL builder."""

from __future__ import annotations

import pytest

from datapulse.explore.models import (
    Dimension,
    DimensionType,
    ExploreCatalog,
    ExploreFilter,
    ExploreModel,
    ExploreQuery,
    JoinPath,
    Metric,
    MetricType,
    SortDirection,
    SortSpec,
)
from datapulse.explore.sql_builder import build_sql

# ---------------------------------------------------------------------------
# Fixtures — minimal catalog for testing
# ---------------------------------------------------------------------------


def _make_catalog(
    *,
    dims: list[Dimension] | None = None,
    metrics: list[Metric] | None = None,
    joins: list[JoinPath] | None = None,
    extra_models: list[ExploreModel] | None = None,
    schema_name: str = "public_marts",
    model_name: str = "fct_sales",
) -> ExploreCatalog:
    """Build a minimal catalog for test cases."""
    if dims is None:
        dims = [
            Dimension(
                name="date", label="Date",
                dimension_type=DimensionType.date, model=model_name,
            ),
            Dimension(
                name="category", label="Category",
                dimension_type=DimensionType.string, model=model_name,
            ),
            Dimension(
                name="region", label="Region",
                dimension_type=DimensionType.string, model=model_name,
            ),
        ]
    if metrics is None:
        metrics = [
            Metric(
                name="total_sales", label="Total Sales",
                metric_type=MetricType.sum, column="net_sales",
                model=model_name,
            ),
            Metric(
                name="avg_quantity", label="Avg Quantity",
                metric_type=MetricType.average, column="quantity",
                model=model_name,
            ),
        ]

    base_model = ExploreModel(
        name=model_name,
        schema_name=schema_name,
        dimensions=dims,
        metrics=metrics,
        joins=joins or [],
    )

    models = [base_model]
    if extra_models:
        models.extend(extra_models)

    return ExploreCatalog(models=models)


# ---------------------------------------------------------------------------
# T6.1 — Basic query builds valid SQL
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBasicQueryBuild:
    def test_single_dimension_single_metric(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "SELECT" in sql
        assert "fct_sales.category" in sql
        assert "SUM(fct_sales.net_sales) AS total_sales" in sql
        assert "FROM public_marts.fct_sales AS fct_sales" in sql
        assert "GROUP BY" in sql
        assert "LIMIT" in sql
        assert params["_limit"] == 500

    def test_dimensions_only_no_group_by(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category", "region"],
            metrics=[],
        )

        sql, params = build_sql(query, catalog)

        assert "fct_sales.category" in sql
        assert "fct_sales.region" in sql
        # No metrics => no GROUP BY
        assert "GROUP BY" not in sql

    def test_metrics_only_no_group_by(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=[],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "SUM(fct_sales.net_sales) AS total_sales" in sql
        assert "GROUP BY" not in sql


# ---------------------------------------------------------------------------
# T6.1 — Multiple dimensions produce GROUP BY
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGroupBy:
    def test_multiple_dimensions_with_metric(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category", "region"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "GROUP BY fct_sales.category, fct_sales.region" in sql

    def test_single_dimension_with_metric(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["date"],
            metrics=["avg_quantity"],
        )

        sql, params = build_sql(query, catalog)

        assert "GROUP BY fct_sales.date" in sql
        assert "AVG(fct_sales.quantity) AS avg_quantity" in sql


# ---------------------------------------------------------------------------
# T6.1 — Filter parameterization works
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterParameterization:
    def test_eq_filter(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="category", operator="eq", value="Electronics")],
        )

        sql, params = build_sql(query, catalog)

        assert "fct_sales.category = :p0" in sql
        assert params["p0"] == "Electronics"

    def test_gt_filter(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="category", operator="gt", value=100)],
        )

        sql, params = build_sql(query, catalog)

        assert "fct_sales.category > :p0" in sql
        assert params["p0"] == 100

    def test_like_filter(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="category", operator="like", value="%elec%")],
        )

        sql, params = build_sql(query, catalog)

        assert "fct_sales.category ILIKE :p0" in sql
        assert params["p0"] == "%elec%"

    def test_in_filter_list(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="category", operator="in", value=["A", "B", "C"])],
        )

        sql, params = build_sql(query, catalog)

        assert "fct_sales.category IN (:p0_0, :p0_1, :p0_2)" in sql
        assert params["p0_0"] == "A"
        assert params["p0_1"] == "B"
        assert params["p0_2"] == "C"

    def test_multiple_filters_produce_and(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[
                ExploreFilter(field="category", operator="eq", value="X"),
                ExploreFilter(field="region", operator="neq", value="Z"),
            ],
        )

        sql, params = build_sql(query, catalog)

        assert "WHERE" in sql
        assert "AND" in sql
        assert params["p0"] == "X"
        assert params["p1"] == "Z"

    def test_unknown_filter_operator_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="category", operator="invalid_op", value="X")],
        )

        with pytest.raises(ValueError, match="Unknown filter operator"):
            build_sql(query, catalog)


# ---------------------------------------------------------------------------
# T6.1 — Invalid column raises ValueError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInvalidColumnRaises:
    def test_unknown_dimension_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["nonexistent_dim"],
            metrics=["total_sales"],
        )

        with pytest.raises(ValueError, match="Unknown dimension"):
            build_sql(query, catalog)

    def test_unknown_metric_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["nonexistent_metric"],
        )

        with pytest.raises(ValueError, match="Unknown metric"):
            build_sql(query, catalog)

    def test_unknown_model_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="nonexistent_model",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        with pytest.raises(ValueError, match="Unknown model"):
            build_sql(query, catalog)

    def test_unsafe_schema_name_raises(self):
        catalog = _make_catalog(schema_name="DROP TABLE; --")
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        with pytest.raises(ValueError, match="Unsafe schema name"):
            build_sql(query, catalog)

    def test_unsafe_filter_field_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            filters=[ExploreFilter(field="DROP TABLE;--", operator="eq", value="x")],
        )

        with pytest.raises(ValueError, match="Unsafe filter field"):
            build_sql(query, catalog)


# ---------------------------------------------------------------------------
# T6.1 — Empty query handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEmptyQueryHandling:
    def test_no_dims_no_metrics_raises(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=[],
            metrics=[],
        )

        with pytest.raises(ValueError, match="At least one dimension or metric"):
            build_sql(query, catalog)


# ---------------------------------------------------------------------------
# T6.1 — LIMIT + ORDER BY included
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLimitAndOrderBy:
    def test_default_limit(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "LIMIT :_limit" in sql
        assert params["_limit"] == 500

    def test_custom_limit(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            limit=100,
        )

        sql, params = build_sql(query, catalog)

        assert params["_limit"] == 100

    def test_explicit_sort(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            sorts=[SortSpec(field="total_sales", direction=SortDirection.asc)],
        )

        sql, params = build_sql(query, catalog)

        assert "ORDER BY total_sales asc" in sql

    def test_default_sort_by_first_metric_desc(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "ORDER BY total_sales DESC" in sql

    def test_invalid_sort_field_ignored(self):
        catalog = _make_catalog()
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
            sorts=[SortSpec(field="nonexistent_field", direction=SortDirection.asc)],
        )

        sql, params = build_sql(query, catalog)

        # Invalid sort field is ignored; falls back to default metric sort
        assert "ORDER BY total_sales DESC" in sql

    def test_no_schema_prefix_when_empty(self):
        catalog = _make_catalog(schema_name="")
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "FROM fct_sales AS fct_sales" in sql


# ---------------------------------------------------------------------------
# T6.1 — Join queries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJoinQueries:
    def test_join_with_dimension_from_joined_model(self):
        dim_customer = ExploreModel(
            name="dim_customer",
            schema_name="public_marts",
            dimensions=[
                Dimension(
                    name="customer_name", label="Customer",
                    dimension_type=DimensionType.string,
                    model="dim_customer",
                ),
            ],
            metrics=[],
            joins=[],
        )
        catalog = _make_catalog(
            joins=[JoinPath(
                join_model="dim_customer",
                sql_on="${fct_sales.customer_id} = ${dim_customer.id}",
            )],
            extra_models=[dim_customer],
        )
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["customer_name"],
            metrics=["total_sales"],
        )

        sql, params = build_sql(query, catalog)

        assert "LEFT JOIN" in sql
        assert "dim_customer" in sql
        assert "GROUP BY dim_customer.customer_name" in sql


# ---------------------------------------------------------------------------
# T6.1 — Aggregation types
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregationTypes:
    @pytest.mark.parametrize(
        "metric_type, expected_sql",
        [
            (MetricType.sum, "SUM("),
            (MetricType.average, "AVG("),
            (MetricType.count, "COUNT("),
            (MetricType.count_distinct, "COUNT(DISTINCT "),
            (MetricType.min, "MIN("),
            (MetricType.max, "MAX("),
        ],
    )
    def test_aggregation_function(self, metric_type: MetricType, expected_sql: str):
        catalog = _make_catalog(
            metrics=[
                Metric(
                    name="test_metric", label="Test",
                    metric_type=metric_type, column="net_sales",
                    model="fct_sales",
                ),
            ],
        )
        query = ExploreQuery(
            model="fct_sales",
            dimensions=["category"],
            metrics=["test_metric"],
        )

        sql, params = build_sql(query, catalog)

        assert expected_sql in sql
