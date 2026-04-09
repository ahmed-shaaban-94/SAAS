{% test unique_combination_of_columns(model, combination_of_columns) %}

-- Generic test: assert that the combination of columns is unique across all rows.
-- Usage in schema.yml:
--   tests:
--     - unique_combination_of_columns:
--         combination_of_columns:
--           - tenant_id
--           - customer_key

SELECT
    {% for col in combination_of_columns %}
    {{ col }},
    {% endfor %}
    COUNT(*) AS n
FROM {{ model }}
GROUP BY
    {% for col in combination_of_columns %}
    {{ col }}{% if not loop.last %},{% endif %}
    {% endfor %}
HAVING COUNT(*) > 1

{% endtest %}
