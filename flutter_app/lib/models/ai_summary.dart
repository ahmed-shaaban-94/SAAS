class AiSummary {
  final String narrative;
  final List<String> keyInsights;
  final List<String> recommendations;
  final DateTime generatedAt;

  const AiSummary({
    required this.narrative,
    required this.keyInsights,
    required this.recommendations,
    required this.generatedAt,
  });

  factory AiSummary.fromJson(Map<String, dynamic> json) => AiSummary(
        narrative: json['narrative'] as String,
        keyInsights: List<String>.from(json['key_insights'] ?? []),
        recommendations: List<String>.from(json['recommendations'] ?? []),
        generatedAt: DateTime.parse(json['generated_at'] as String),
      );
}

class AnomalyReport {
  final List<AnomalyInsight> anomalies;
  final String summary;
  final DateTime generatedAt;

  const AnomalyReport({
    required this.anomalies,
    required this.summary,
    required this.generatedAt,
  });

  factory AnomalyReport.fromJson(Map<String, dynamic> json) => AnomalyReport(
        anomalies: (json['anomalies'] as List)
            .map((e) => AnomalyInsight.fromJson(e))
            .toList(),
        summary: json['summary'] as String,
        generatedAt: DateTime.parse(json['generated_at'] as String),
      );
}

class AnomalyInsight {
  final String metric;
  final String description;
  final String severity;
  final double impact;

  const AnomalyInsight({
    required this.metric,
    required this.description,
    required this.severity,
    required this.impact,
  });

  factory AnomalyInsight.fromJson(Map<String, dynamic> json) =>
      AnomalyInsight(
        metric: json['metric'] as String,
        description: json['description'] as String,
        severity: json['severity'] as String,
        impact: (json['impact'] as num).toDouble(),
      );
}

class ChangeNarrative {
  final String narrative;
  final List<ChangeDriver> drivers;
  final DateTime generatedAt;

  const ChangeNarrative({
    required this.narrative,
    required this.drivers,
    required this.generatedAt,
  });

  factory ChangeNarrative.fromJson(Map<String, dynamic> json) =>
      ChangeNarrative(
        narrative: json['narrative'] as String,
        drivers: (json['drivers'] as List?)
                ?.map((e) => ChangeDriver.fromJson(e))
                .toList() ??
            [],
        generatedAt: DateTime.parse(json['generated_at'] as String),
      );
}

class ChangeDriver {
  final String dimension;
  final String name;
  final double impact;
  final String direction; // increase, decrease

  const ChangeDriver({
    required this.dimension,
    required this.name,
    required this.impact,
    required this.direction,
  });

  factory ChangeDriver.fromJson(Map<String, dynamic> json) => ChangeDriver(
        dimension: json['dimension'] as String,
        name: json['name'] as String,
        impact: (json['impact'] as num).toDouble(),
        direction: json['direction'] as String,
      );
}
