class FilterOption {
  final String key;
  final String label;

  const FilterOption({required this.key, required this.label});

  factory FilterOption.fromJson(Map<String, dynamic> json) => FilterOption(
        key: json['key'] as String,
        label: json['label'] as String,
      );
}

class FilterOptions {
  final List<String> categories;
  final List<String> brands;
  final List<FilterOption> sites;
  final List<FilterOption> staff;

  const FilterOptions({
    required this.categories,
    required this.brands,
    required this.sites,
    required this.staff,
  });

  factory FilterOptions.fromJson(Map<String, dynamic> json) => FilterOptions(
        categories: List<String>.from(json['categories'] ?? []),
        brands: List<String>.from(json['brands'] ?? []),
        sites: (json['sites'] as List?)
                ?.map((e) => FilterOption.fromJson(e))
                .toList() ??
            [],
        staff: (json['staff'] as List?)
                ?.map((e) => FilterOption.fromJson(e))
                .toList() ??
            [],
      );
}

class AnalyticsFilter {
  final DateTime? startDate;
  final DateTime? endDate;
  final String? siteKey;
  final String? category;
  final String? brand;
  final String? staffKey;
  final int limit;

  const AnalyticsFilter({
    this.startDate,
    this.endDate,
    this.siteKey,
    this.category,
    this.brand,
    this.staffKey,
    this.limit = 10,
  });

  Map<String, dynamic> toQueryParams() {
    final params = <String, dynamic>{};
    if (startDate != null) {
      params['start_date'] =
          '${startDate!.year}-${startDate!.month.toString().padLeft(2, '0')}-${startDate!.day.toString().padLeft(2, '0')}';
    }
    if (endDate != null) {
      params['end_date'] =
          '${endDate!.year}-${endDate!.month.toString().padLeft(2, '0')}-${endDate!.day.toString().padLeft(2, '0')}';
    }
    if (siteKey != null) params['site_key'] = siteKey;
    if (category != null) params['category'] = category;
    if (brand != null) params['brand'] = brand;
    if (staffKey != null) params['staff_key'] = staffKey;
    params['limit'] = limit;
    return params;
  }

  AnalyticsFilter copyWith({
    DateTime? startDate,
    DateTime? endDate,
    String? siteKey,
    String? category,
    String? brand,
    String? staffKey,
    int? limit,
  }) {
    return AnalyticsFilter(
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      siteKey: siteKey ?? this.siteKey,
      category: category ?? this.category,
      brand: brand ?? this.brand,
      staffKey: staffKey ?? this.staffKey,
      limit: limit ?? this.limit,
    );
  }
}
