"""Named SQL constants for KpiRepository.

Extracted from kpi_repository.py to separate SQL from Python orchestration
logic, improving readability and making query changes easier to diff.

Note: ``KPI_FCT_SALES_TEMPLATE`` uses Python str.format() placeholders
(``{join_clause}``, ``{where_clause}``, etc.) that are substituted in
``_get_kpi_from_fct_sales``.  These placeholders are built from validated
filter objects — never from raw user input.
"""

# ── Date range ────────────────────────────────────────────────────────────────

DATE_RANGE_SQL = """
    SELECT MIN(full_date), MAX(full_date)
    FROM public_marts.metrics_summary
"""

# ── Filter options ────────────────────────────────────────────────────────────

FILTER_OPTIONS_SQL = """
    SELECT * FROM (
        SELECT 'category' AS type, drug_category AS value, NULL::int AS key
        FROM public_marts.agg_sales_by_product
        WHERE drug_category IS NOT NULL
        GROUP BY drug_category
        ORDER BY drug_category
        LIMIT 500
    ) cats
    UNION ALL
    SELECT * FROM (
        SELECT 'brand', drug_brand, NULL::int
        FROM public_marts.agg_sales_by_product
        WHERE drug_brand IS NOT NULL
        GROUP BY drug_brand
        ORDER BY drug_brand
        LIMIT 500
    ) brands
    UNION ALL
    SELECT * FROM (
        SELECT 'site', site_name, site_key
        FROM public_marts.agg_sales_by_site
        WHERE site_key > 0
        GROUP BY site_key, site_name
        ORDER BY site_name
        LIMIT 100
    ) sites
    UNION ALL
    SELECT * FROM (
        SELECT 'staff', staff_name, staff_key
        FROM public_marts.agg_sales_by_staff
        WHERE staff_key > 0
        GROUP BY staff_key, staff_name
        ORDER BY staff_name
        LIMIT 500
    ) stf
    ORDER BY type, value
"""

# ── KPI summary — single day, unified CTE ────────────────────────────────────

KPI_SUMMARY_DAILY_SQL = """
    WITH daily AS (
        SELECT daily_gross_amount, 0 AS daily_discount,
               mtd_gross_amount, ytd_gross_amount,
               daily_quantity,
               daily_transactions, daily_unique_customers,
               daily_returns, mtd_transactions, ytd_transactions
        FROM public_marts.metrics_summary
        WHERE full_date = :target_date
    ),
    basket AS (
        SELECT ROUND(
            SUM(total_sales) / NULLIF(SUM(unique_customers), 0),
            2
        ) AS avg_basket_size
        FROM public_marts.agg_sales_daily
        WHERE date_key = :date_key
    ),
    prev_month AS (
        SELECT mtd_gross_amount
        FROM public_marts.metrics_summary
        WHERE full_date = CAST(
            CAST(:target_date AS date) - INTERVAL '1 month'
        AS date)
    ),
    prev_year AS (
        SELECT ytd_gross_amount
        FROM public_marts.metrics_summary
        WHERE full_date = CAST(
            CAST(:target_date AS date) - INTERVAL '1 year'
        AS date)
    ),
    sparkline AS (
        SELECT
            json_agg(
                json_build_object('period', full_date, 'value', daily_gross_amount)
                ORDER BY full_date
            ) AS points,
            json_agg(
                json_build_object('period', full_date, 'value', daily_transactions)
                ORDER BY full_date
            ) AS orders_points
        FROM public_marts.metrics_summary
        WHERE full_date BETWEEN :sparkline_start AND :target_date
    ),
    mom_history AS (
        SELECT json_agg(mtd_gross_amount ORDER BY full_date) AS vals
        FROM public_marts.metrics_summary
        WHERE full_date IN (
            SELECT (CAST(:target_date AS date) - (n || ' months')::interval)::date
            FROM generate_series(1, 12) AS n
        )
    ),
    yoy_history AS (
        SELECT json_agg(ytd_gross_amount ORDER BY full_date) AS vals
        FROM public_marts.metrics_summary
        WHERE full_date IN (
            SELECT (CAST(:target_date AS date) - (n || ' years')::interval)::date
            FROM generate_series(1, 5) AS n
        )
    )
    SELECT
        d.daily_gross_amount,
        d.daily_discount,
        d.mtd_gross_amount,
        d.ytd_gross_amount,
        d.daily_quantity,
        d.daily_transactions,
        d.daily_unique_customers,
        d.daily_returns,
        d.mtd_transactions,
        d.ytd_transactions,
        b.avg_basket_size,
        pm.mtd_gross_amount AS prev_month_mtd,
        py.ytd_gross_amount AS prev_year_ytd,
        sp.points AS sparkline_points,
        sp.orders_points AS sparkline_orders_points,
        mh.vals AS mom_history,
        yh.vals AS yoy_history
    FROM daily d
    CROSS JOIN basket b
    CROSS JOIN prev_month pm
    CROSS JOIN prev_year py
    CROSS JOIN sparkline sp
    CROSS JOIN mom_history mh
    CROSS JOIN yoy_history yh
"""

# ── KPI via fct_sales — dynamic template with dimension JOINs ────────────────
# Placeholders substituted by _get_kpi_from_fct_sales:
#   {join_clause}  — optional INNER JOIN to dim_product
#   {where_clause} — base date + dimension WHERE predicates
#   {prev_where}   — same dimensions, shifted to previous period
#   {mtd_where}    — same dimensions, MTD window
#   {ytd_where}    — same dimensions, YTD window

KPI_FCT_SALES_TEMPLATE = """
    WITH range_agg AS (
        SELECT
            ROUND(SUM(f.sales), 2) AS period_net,
            SUM(f.quantity)::NUMERIC(18,4) AS total_quantity,
            COUNT(*) FILTER (WHERE NOT f.is_return)::INT AS total_transactions,
            COUNT(*) FILTER (WHERE f.is_return)::INT AS total_returns,
            COUNT(DISTINCT f.customer_key)::INT AS total_customers
        FROM public_marts.fct_sales f
        {join_clause}
        WHERE {where_clause}
    ),
    basket AS (
        SELECT ROUND(
            SUM(f.sales) FILTER (WHERE NOT f.is_return)
            / NULLIF(COUNT(DISTINCT f.invoice_id) FILTER (WHERE NOT f.is_return), 0),
            2
        ) AS avg_basket_size
        FROM public_marts.fct_sales f
        {join_clause}
        WHERE {where_clause}
    ),
    prev_period AS (
        SELECT ROUND(SUM(f.sales), 2) AS prev_net
        FROM public_marts.fct_sales f
        {join_clause}
        WHERE {prev_where}
    ),
    mtd_agg AS (
        SELECT
            ROUND(SUM(f.sales), 2) AS mtd_gross,
            COUNT(*) FILTER (WHERE NOT f.is_return)::INT AS mtd_transactions
        FROM public_marts.fct_sales f
        {join_clause}
        WHERE {mtd_where}
    ),
    ytd_agg AS (
        SELECT
            ROUND(SUM(f.sales), 2) AS ytd_gross,
            COUNT(*) FILTER (WHERE NOT f.is_return)::INT AS ytd_transactions
        FROM public_marts.fct_sales f
        {join_clause}
        WHERE {ytd_where}
    ),
    sparkline AS (
        SELECT json_agg(
            json_build_object('period', d.full_date, 'value', COALESCE(day_total, 0))
            ORDER BY d.full_date
        ) AS points
        FROM public_marts.dim_date d
        LEFT JOIN (
            SELECT f.date_key, ROUND(SUM(f.sales), 2) AS day_total
            FROM public_marts.fct_sales f
            {join_clause}
            WHERE {where_clause} AND f.date_key >= :spark_start_key
            GROUP BY f.date_key
        ) s ON d.date_key = s.date_key
        WHERE d.date_key BETWEEN :spark_start_key AND :end_key
    )
    SELECT
        r.period_net,
        r.total_quantity,
        r.total_transactions,
        r.total_returns,
        r.total_customers,
        b.avg_basket_size,
        p.prev_net,
        m.mtd_gross,
        m.mtd_transactions,
        y.ytd_gross,
        y.ytd_transactions,
        sp.points AS sparkline_points
    FROM range_agg r
    CROSS JOIN basket b
    CROSS JOIN prev_period p
    CROSS JOIN mtd_agg m
    CROSS JOIN ytd_agg y
    CROSS JOIN sparkline sp
"""

# ── KPI summary range — pre-aggregated metrics_summary path ──────────────────

KPI_SUMMARY_RANGE_SQL = """
    WITH range_agg AS (
        SELECT
            ROUND(SUM(daily_gross_amount), 2) AS period_net,
            SUM(daily_quantity)::NUMERIC(18,4) AS total_quantity,
            SUM(daily_transactions)::INT     AS total_transactions,
            SUM(daily_returns)::INT           AS total_returns,
            SUM(daily_unique_customers)::INT  AS total_customers
        FROM public_marts.metrics_summary
        WHERE full_date BETWEEN :start_date AND :end_date
    ),
    last_day AS (
        SELECT mtd_gross_amount, ytd_gross_amount,
               mtd_transactions, ytd_transactions
        FROM public_marts.metrics_summary
        WHERE full_date = :end_date
    ),
    basket AS (
        SELECT ROUND(
            SUM(total_sales) / NULLIF(SUM(transaction_count), 0),
            2
        ) AS avg_basket_size
        FROM public_marts.agg_sales_daily
        WHERE date_key BETWEEN :start_key AND :end_key
    ),
    prev_period AS (
        SELECT ROUND(SUM(daily_gross_amount), 2) AS prev_net
        FROM public_marts.metrics_summary
        WHERE full_date BETWEEN
            CAST(:start_date AS date) - (:end_date - :start_date + 1) * INTERVAL '1 day'
            AND CAST(:start_date AS date) - INTERVAL '1 day'
    ),
    sparkline AS (
        SELECT json_agg(
            json_build_object('period', full_date, 'value', daily_gross_amount)
            ORDER BY full_date
        ) AS points
        FROM public_marts.metrics_summary
        WHERE full_date BETWEEN :sparkline_start AND :end_date
    )
    SELECT
        r.period_net,
        r.total_quantity,
        r.total_transactions,
        r.total_returns,
        r.total_customers,
        l.mtd_gross_amount,
        l.ytd_gross_amount,
        l.mtd_transactions,
        l.ytd_transactions,
        b.avg_basket_size,
        p.prev_net,
        sp.points AS sparkline_points
    FROM range_agg r
    CROSS JOIN last_day l
    CROSS JOIN basket b
    CROSS JOIN prev_period p
    CROSS JOIN sparkline sp
"""

# ── Sparkline ─────────────────────────────────────────────────────────────────

KPI_SPARKLINE_SQL = """
    SELECT full_date AS period, daily_gross_amount AS value
    FROM public_marts.metrics_summary
    WHERE full_date BETWEEN :start_date AND :target_date
    ORDER BY full_date
"""
