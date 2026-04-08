class ExploreModel {
  final String name;
  final String? description;
  final List<ExploreDimension> dimensions;
  final List<ExploreMetric> metrics;

  const ExploreModel({
    required this.name,
    this.description,
    required this.dimensions,
    required this.metrics,
  });

  factory ExploreModel.fromJson(Map<String, dynamic> json) => ExploreModel(
        name: json['name'] as String,
        description: json['description'] as String?,
        dimensions: (json['dimensions'] as List?)
                ?.map((e) => ExploreDimension.fromJson(e))
                .toList() ??
            [],
        metrics: (json['metrics'] as List?)
                ?.map((e) => ExploreMetric.fromJson(e))
                .toList() ??
            [],
      );
}

class ExploreDimension {
  final String name;
  final String type;
  final String? description;

  const ExploreDimension({
    required this.name,
    required this.type,
    this.description,
  });

  factory ExploreDimension.fromJson(Map<String, dynamic> json) =>
      ExploreDimension(
        name: json['name'] as String,
        type: json['type'] as String,
        description: json['description'] as String?,
      );
}

class ExploreMetric {
  final String name;
  final String type;
  final String? description;
  final String? aggregation;

  const ExploreMetric({
    required this.name,
    required this.type,
    this.description,
    this.aggregation,
  });

  factory ExploreMetric.fromJson(Map<String, dynamic> json) => ExploreMetric(
        name: json['name'] as String,
        type: json['type'] as String,
        description: json['description'] as String?,
        aggregation: json['aggregation'] as String?,
      );
}

class ExploreResult {
  final String sql;
  final List<String> columns;
  final List<Map<String, dynamic>> rows;
  final int rowCount;

  const ExploreResult({
    required this.sql,
    required this.columns,
    required this.rows,
    required this.rowCount,
  });

  factory ExploreResult.fromJson(Map<String, dynamic> json) => ExploreResult(
        sql: json['sql'] as String,
        columns: List<String>.from(json['columns'] ?? []),
        rows: (json['rows'] as List?)
                ?.map((e) => Map<String, dynamic>.from(e))
                .toList() ??
            [],
        rowCount: json['row_count'] as int? ?? 0,
      );
}
