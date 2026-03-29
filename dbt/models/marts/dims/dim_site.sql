{{
    config(
        materialized='table',
        schema='marts',
        post_hook=[
            "ALTER TABLE {{ this }} ENABLE ROW LEVEL SECURITY",
            "ALTER TABLE {{ this }} FORCE ROW LEVEL SECURITY",
            "DROP POLICY IF EXISTS owner_all ON {{ this }}",
            "CREATE POLICY owner_all ON {{ this }} FOR ALL TO datapulse USING (true) WITH CHECK (true)",
            "DROP POLICY IF EXISTS reader_tenant ON {{ this }}",
            "CREATE POLICY reader_tenant ON {{ this }} FOR SELECT TO datapulse_reader USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INT)"
        ]
    )
}}

-- Site/location dimension
-- SCD Type 1: latest attribute wins
-- Includes area_manager (site-level geographic grouping)
-- Includes governorate / governorate_ar for Egypt shape map in Power BI
-- key = -1 reserved for Unknown/Unassigned

WITH ranked AS (
    SELECT
        tenant_id,
        site_code,
        site_name,
        area_manager,
        ROW_NUMBER() OVER (
            PARTITION BY tenant_id, site_code
            ORDER BY invoice_date DESC
        ) AS rn
    FROM {{ ref('stg_sales') }}
    WHERE site_code IS NOT NULL
),

sites AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY tenant_id, site_code)::INT AS site_key,
        tenant_id,
        site_code,
        site_name,
        area_manager
    FROM ranked
    WHERE rn = 1
)

SELECT
    site_key,
    tenant_id,
    site_code,
    site_name,
    area_manager,
    -- Governorate mapping for Egypt shape map (Power BI)
    -- Maps site_name / area_manager patterns to Egyptian governorates
    CASE
        -- Qalyubia
        WHEN site_name ~* 'شبرا|الخيمة|بنها|قليوب|طوخ|القناطر'
          OR area_manager ~* 'قليوب'
            THEN 'Qalyubia'
        -- Giza
        WHEN site_name ~* 'جيزة|الجيزة|هرم|الهرم|فيصل|الدقي|المهندسين|العجوزة|بولاق|اكتوبر|6 أكتوبر|الشيخ زايد|زايد'
          OR area_manager ~* 'جيزة|اكتوبر|زايد'
            THEN 'Giza'
        -- Alexandria
        WHEN site_name ~* 'اسكندرية|الاسكندرية|الإسكندرية|سيدي بشر|محطة الرمل|سموحة|ستانلي|المنتزه|العجمي'
          OR area_manager ~* 'اسكندرية|الاسكندرية'
            THEN 'Alexandria'
        -- Dakahlia
        WHEN site_name ~* 'المنصورة|منصورة|دكرنس|ميت غمر|دقهلية'
          OR area_manager ~* 'دقهلية|منصورة'
            THEN 'Dakahlia'
        -- Sharqia
        WHEN site_name ~* 'الزقازيق|زقازيق|شرقية|العاشر من رمضان|بلبيس|ههيا'
          OR area_manager ~* 'شرقية|زقازيق'
            THEN 'Sharqia'
        -- Gharbia
        WHEN site_name ~* 'طنطا|المحلة|غربية|زفتى|سمنود'
          OR area_manager ~* 'غربية|طنطا'
            THEN 'Gharbia'
        -- Monufia
        WHEN site_name ~* 'شبين الكوم|منوفية|منوف|السادات|قويسنا'
          OR area_manager ~* 'منوفية'
            THEN 'Monufia'
        -- Beheira
        WHEN site_name ~* 'دمنهور|بحيرة|كفر الدوار|رشيد'
          OR area_manager ~* 'بحيرة|دمنهور'
            THEN 'Beheira'
        -- Kafr El Sheikh
        WHEN site_name ~* 'كفر الشيخ|دسوق|بيلا'
          OR area_manager ~* 'كفر الشيخ'
            THEN 'Kafr El Sheikh'
        -- Damietta
        WHEN site_name ~* 'دمياط'
          OR area_manager ~* 'دمياط'
            THEN 'Damietta'
        -- Port Said
        WHEN site_name ~* 'بورسعيد'
          OR area_manager ~* 'بورسعيد'
            THEN 'Port Said'
        -- Ismailia
        WHEN site_name ~* 'اسماعيلية|الإسماعيلية'
          OR area_manager ~* 'اسماعيلية'
            THEN 'Ismailia'
        -- Suez
        WHEN site_name ~* 'السويس|سويس'
          OR area_manager ~* 'سويس'
            THEN 'Suez'
        -- Fayoum
        WHEN site_name ~* 'الفيوم|فيوم'
          OR area_manager ~* 'فيوم'
            THEN 'Fayoum'
        -- Beni Suef
        WHEN site_name ~* 'بني سويف'
          OR area_manager ~* 'بني سويف'
            THEN 'Beni Suef'
        -- Minya
        WHEN site_name ~* 'المنيا|منيا'
          OR area_manager ~* 'منيا'
            THEN 'Minya'
        -- Assiut
        WHEN site_name ~* 'اسيوط|أسيوط'
          OR area_manager ~* 'اسيوط|أسيوط'
            THEN 'Assiut'
        -- Sohag
        WHEN site_name ~* 'سوهاج'
          OR area_manager ~* 'سوهاج'
            THEN 'Sohag'
        -- Luxor
        WHEN site_name ~* 'الأقصر|الاقصر|اقصر'
          OR area_manager ~* 'أقصر|اقصر'
            THEN 'Luxor'
        -- Aswan
        WHEN site_name ~* 'اسوان|أسوان'
          OR area_manager ~* 'اسوان|أسوان'
            THEN 'Aswan'
        -- Red Sea
        WHEN site_name ~* 'الغردقة|غردقة|البحر الأحمر|البحر الاحمر|مرسى علم'
          OR area_manager ~* 'البحر الأحمر|غردقة'
            THEN 'Red Sea'
        -- Default: Cairo (most common for pharmacy chains)
        ELSE 'Cairo'
    END AS governorate,
    CASE
        WHEN site_name ~* 'شبرا|الخيمة|بنها|قليوب|طوخ|القناطر'
          OR area_manager ~* 'قليوب'
            THEN 'القليوبية'
        WHEN site_name ~* 'جيزة|الجيزة|هرم|الهرم|فيصل|الدقي|المهندسين|العجوزة|بولاق|اكتوبر|6 أكتوبر|الشيخ زايد|زايد'
          OR area_manager ~* 'جيزة|اكتوبر|زايد'
            THEN 'الجيزة'
        WHEN site_name ~* 'اسكندرية|الاسكندرية|الإسكندرية|سيدي بشر|محطة الرمل|سموحة|ستانلي|المنتزه|العجمي'
          OR area_manager ~* 'اسكندرية|الاسكندرية'
            THEN 'الإسكندرية'
        WHEN site_name ~* 'المنصورة|منصورة|دكرنس|ميت غمر|دقهلية'
          OR area_manager ~* 'دقهلية|منصورة'
            THEN 'الدقهلية'
        WHEN site_name ~* 'الزقازيق|زقازيق|شرقية|العاشر من رمضان|بلبيس|ههيا'
          OR area_manager ~* 'شرقية|زقازيق'
            THEN 'الشرقية'
        WHEN site_name ~* 'طنطا|المحلة|غربية|زفتى|سمنود'
          OR area_manager ~* 'غربية|طنطا'
            THEN 'الغربية'
        WHEN site_name ~* 'شبين الكوم|منوفية|منوف|السادات|قويسنا'
          OR area_manager ~* 'منوفية'
            THEN 'المنوفية'
        WHEN site_name ~* 'دمنهور|بحيرة|كفر الدوار|رشيد'
          OR area_manager ~* 'بحيرة|دمنهور'
            THEN 'البحيرة'
        WHEN site_name ~* 'كفر الشيخ|دسوق|بيلا'
          OR area_manager ~* 'كفر الشيخ'
            THEN 'كفر الشيخ'
        WHEN site_name ~* 'دمياط'
          OR area_manager ~* 'دمياط'
            THEN 'دمياط'
        WHEN site_name ~* 'بورسعيد'
          OR area_manager ~* 'بورسعيد'
            THEN 'بورسعيد'
        WHEN site_name ~* 'اسماعيلية|الإسماعيلية'
          OR area_manager ~* 'اسماعيلية'
            THEN 'الإسماعيلية'
        WHEN site_name ~* 'السويس|سويس'
          OR area_manager ~* 'سويس'
            THEN 'السويس'
        WHEN site_name ~* 'الفيوم|فيوم'
          OR area_manager ~* 'فيوم'
            THEN 'الفيوم'
        WHEN site_name ~* 'بني سويف'
          OR area_manager ~* 'بني سويف'
            THEN 'بني سويف'
        WHEN site_name ~* 'المنيا|منيا'
          OR area_manager ~* 'منيا'
            THEN 'المنيا'
        WHEN site_name ~* 'اسيوط|أسيوط'
          OR area_manager ~* 'اسيوط|أسيوط'
            THEN 'أسيوط'
        WHEN site_name ~* 'سوهاج'
          OR area_manager ~* 'سوهاج'
            THEN 'سوهاج'
        WHEN site_name ~* 'الأقصر|الاقصر|اقصر'
          OR area_manager ~* 'أقصر|اقصر'
            THEN 'الأقصر'
        WHEN site_name ~* 'اسوان|أسوان'
          OR area_manager ~* 'اسوان|أسوان'
            THEN 'أسوان'
        WHEN site_name ~* 'الغردقة|غردقة|البحر الأحمر|البحر الاحمر|مرسى علم'
          OR area_manager ~* 'البحر الأحمر|غردقة'
            THEN 'البحر الأحمر'
        ELSE 'القاهرة'
    END AS governorate_ar
FROM sites

UNION ALL

SELECT
    -1                 AS site_key,
    1                  AS tenant_id,
    '__UNKNOWN__'      AS site_code,
    'Unknown'          AS site_name,
    'Unknown'          AS area_manager,
    'Unknown'          AS governorate,
    'Unknown'          AS governorate_ar
