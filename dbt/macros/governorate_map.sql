{# Governorate mapping macro for Egyptian governorates.
   Maps site_name / area_manager patterns to governorate names.
   Parameters:
     - site_col: column name for site (e.g. 'site_name')
     - manager_col: column name for area manager (e.g. 'area_manager')
     - lang: 'en' for English names, 'ar' for Arabic names
#}

{% macro governorate_map(site_col, manager_col, lang='en') %}
CASE
    -- Qalyubia
    WHEN {{ site_col }} ~* 'شبرا|الخيمة|بنها|قليوب|طوخ|القناطر'
      OR {{ manager_col }} ~* 'قليوب'
        THEN {{ "'Qalyubia'" if lang == 'en' else "'القليوبية'" }}
    -- Giza
    WHEN {{ site_col }} ~* 'جيزة|الجيزة|هرم|الهرم|فيصل|الدقي|المهندسين|العجوزة|بولاق|اكتوبر|6 أكتوبر|الشيخ زايد|زايد'
      OR {{ manager_col }} ~* 'جيزة|اكتوبر|زايد'
        THEN {{ "'Giza'" if lang == 'en' else "'الجيزة'" }}
    -- Alexandria
    WHEN {{ site_col }} ~* 'اسكندرية|الاسكندرية|الإسكندرية|سيدي بشر|محطة الرمل|سموحة|ستانلي|المنتزه|العجمي'
      OR {{ manager_col }} ~* 'اسكندرية|الاسكندرية'
        THEN {{ "'Alexandria'" if lang == 'en' else "'الإسكندرية'" }}
    -- Dakahlia
    WHEN {{ site_col }} ~* 'المنصورة|منصورة|دكرنس|ميت غمر|دقهلية'
      OR {{ manager_col }} ~* 'دقهلية|منصورة'
        THEN {{ "'Dakahlia'" if lang == 'en' else "'الدقهلية'" }}
    -- Sharqia
    WHEN {{ site_col }} ~* 'الزقازيق|زقازيق|شرقية|العاشر من رمضان|بلبيس|ههيا'
      OR {{ manager_col }} ~* 'شرقية|زقازيق'
        THEN {{ "'Sharqia'" if lang == 'en' else "'الشرقية'" }}
    -- Gharbia
    WHEN {{ site_col }} ~* 'طنطا|المحلة|غربية|زفتى|سمنود'
      OR {{ manager_col }} ~* 'غربية|طنطا'
        THEN {{ "'Gharbia'" if lang == 'en' else "'الغربية'" }}
    -- Monufia
    WHEN {{ site_col }} ~* 'شبين الكوم|منوفية|منوف|السادات|قويسنا'
      OR {{ manager_col }} ~* 'منوفية'
        THEN {{ "'Monufia'" if lang == 'en' else "'المنوفية'" }}
    -- Beheira
    WHEN {{ site_col }} ~* 'دمنهور|بحيرة|كفر الدوار|رشيد'
      OR {{ manager_col }} ~* 'بحيرة|دمنهور'
        THEN {{ "'Beheira'" if lang == 'en' else "'البحيرة'" }}
    -- Kafr El Sheikh
    WHEN {{ site_col }} ~* 'كفر الشيخ|دسوق|بيلا'
      OR {{ manager_col }} ~* 'كفر الشيخ'
        THEN {{ "'Kafr El Sheikh'" if lang == 'en' else "'كفر الشيخ'" }}
    -- Damietta
    WHEN {{ site_col }} ~* 'دمياط'
      OR {{ manager_col }} ~* 'دمياط'
        THEN {{ "'Damietta'" if lang == 'en' else "'دمياط'" }}
    -- Port Said
    WHEN {{ site_col }} ~* 'بورسعيد'
      OR {{ manager_col }} ~* 'بورسعيد'
        THEN {{ "'Port Said'" if lang == 'en' else "'بورسعيد'" }}
    -- Ismailia
    WHEN {{ site_col }} ~* 'اسماعيلية|الإسماعيلية'
      OR {{ manager_col }} ~* 'اسماعيلية'
        THEN {{ "'Ismailia'" if lang == 'en' else "'الإسماعيلية'" }}
    -- Suez
    WHEN {{ site_col }} ~* 'السويس|سويس'
      OR {{ manager_col }} ~* 'سويس'
        THEN {{ "'Suez'" if lang == 'en' else "'السويس'" }}
    -- Fayoum
    WHEN {{ site_col }} ~* 'الفيوم|فيوم'
      OR {{ manager_col }} ~* 'فيوم'
        THEN {{ "'Fayoum'" if lang == 'en' else "'الفيوم'" }}
    -- Beni Suef
    WHEN {{ site_col }} ~* 'بني سويف'
      OR {{ manager_col }} ~* 'بني سويف'
        THEN {{ "'Beni Suef'" if lang == 'en' else "'بني سويف'" }}
    -- Minya
    WHEN {{ site_col }} ~* 'المنيا|منيا'
      OR {{ manager_col }} ~* 'منيا'
        THEN {{ "'Minya'" if lang == 'en' else "'المنيا'" }}
    -- Assiut
    WHEN {{ site_col }} ~* 'اسيوط|أسيوط'
      OR {{ manager_col }} ~* 'اسيوط|أسيوط'
        THEN {{ "'Assiut'" if lang == 'en' else "'أسيوط'" }}
    -- Sohag
    WHEN {{ site_col }} ~* 'سوهاج'
      OR {{ manager_col }} ~* 'سوهاج'
        THEN {{ "'Sohag'" if lang == 'en' else "'سوهاج'" }}
    -- Luxor
    WHEN {{ site_col }} ~* 'الأقصر|الاقصر|اقصر'
      OR {{ manager_col }} ~* 'أقصر|اقصر'
        THEN {{ "'Luxor'" if lang == 'en' else "'الأقصر'" }}
    -- Aswan
    WHEN {{ site_col }} ~* 'اسوان|أسوان'
      OR {{ manager_col }} ~* 'اسوان|أسوان'
        THEN {{ "'Aswan'" if lang == 'en' else "'أسوان'" }}
    -- Red Sea
    WHEN {{ site_col }} ~* 'الغردقة|غردقة|البحر الأحمر|البحر الاحمر|مرسى علم'
      OR {{ manager_col }} ~* 'البحر الأحمر|غردقة'
        THEN {{ "'Red Sea'" if lang == 'en' else "'البحر الأحمر'" }}
    -- Default: Cairo (most common for pharmacy chains)
    ELSE {{ "'Cairo'" if lang == 'en' else "'القاهرة'" }}
END
{% endmacro %}
