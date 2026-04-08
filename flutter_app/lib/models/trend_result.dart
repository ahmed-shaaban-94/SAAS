class TimeSeriesPoint {
  final String period;
  final double value;

  const TimeSeriesPoint({required this.period, required this.value});

  factory TimeSeriesPoint.fromJson(Map<String, dynamic> json) =>
      TimeSeriesPoint(
        period: json['period'] as String,
        value: (json['value'] as num).toDouble(),
      );
}

class TrendStats {
  final double? zScore;
  final double? cv;
  final String? significance;

  const TrendStats({this.zScore, this.cv, this.significance});

  factory TrendStats.fromJson(Map<String, dynamic> json) => TrendStats(
        zScore: (json['z_score'] as num?)?.toDouble(),
        cv: (json['cv'] as num?)?.toDouble(),
        significance: json['significance'] as String?,
      );
}

class TrendResult {
  final List<TimeSeriesPoint> points;
  final double total;
  final double average;
  final double minimum;
  final double maximum;
  final double? growthPct;
  final TrendStats? stats;

  const TrendResult({
    required this.points,
    required this.total,
    required this.average,
    required this.minimum,
    required this.maximum,
    this.growthPct,
    this.stats,
  });

  factory TrendResult.fromJson(Map<String, dynamic> json) => TrendResult(
        points: (json['points'] as List)
            .map((e) => TimeSeriesPoint.fromJson(e))
            .toList(),
        total: (json['total'] as num).toDouble(),
        average: (json['average'] as num).toDouble(),
        minimum: (json['minimum'] as num).toDouble(),
        maximum: (json['maximum'] as num).toDouble(),
        growthPct: (json['growth_pct'] as num?)?.toDouble(),
        stats: json['stats'] != null
            ? TrendStats.fromJson(json['stats'])
            : null,
      );
}
