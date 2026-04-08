class AnomalyAlert {
  final String id;
  final String metric;
  final String dimension;
  final String dimensionValue;
  final double expectedValue;
  final double actualValue;
  final double deviation;
  final String severity; // low, medium, high, critical
  final bool acknowledged;
  final DateTime detectedAt;

  const AnomalyAlert({
    required this.id,
    required this.metric,
    required this.dimension,
    required this.dimensionValue,
    required this.expectedValue,
    required this.actualValue,
    required this.deviation,
    required this.severity,
    required this.acknowledged,
    required this.detectedAt,
  });

  double get deviationPct =>
      expectedValue != 0 ? ((actualValue - expectedValue) / expectedValue) * 100 : 0;

  factory AnomalyAlert.fromJson(Map<String, dynamic> json) => AnomalyAlert(
        id: json['id'] as String,
        metric: json['metric'] as String,
        dimension: json['dimension'] as String,
        dimensionValue: json['dimension_value'] as String,
        expectedValue: (json['expected_value'] as num).toDouble(),
        actualValue: (json['actual_value'] as num).toDouble(),
        deviation: (json['deviation'] as num).toDouble(),
        severity: json['severity'] as String,
        acknowledged: json['acknowledged'] as bool? ?? false,
        detectedAt: DateTime.parse(json['detected_at'] as String),
      );
}
