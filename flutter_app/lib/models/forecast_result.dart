import 'trend_result.dart';

class ForecastPoint {
  final String period;
  final double actual;
  final double? predicted;
  final double? lowerBound;
  final double? upperBound;

  const ForecastPoint({
    required this.period,
    required this.actual,
    this.predicted,
    this.lowerBound,
    this.upperBound,
  });

  factory ForecastPoint.fromJson(Map<String, dynamic> json) => ForecastPoint(
        period: json['period'] as String,
        actual: (json['actual'] as num).toDouble(),
        predicted: (json['predicted'] as num?)?.toDouble(),
        lowerBound: (json['lower_bound'] as num?)?.toDouble(),
        upperBound: (json['upper_bound'] as num?)?.toDouble(),
      );
}

class ForecastResult {
  final List<ForecastPoint> points;
  final double? nextPeriodForecast;
  final double? confidence;
  final String? granularity;

  const ForecastResult({
    required this.points,
    this.nextPeriodForecast,
    this.confidence,
    this.granularity,
  });

  factory ForecastResult.fromJson(Map<String, dynamic> json) => ForecastResult(
        points: (json['points'] as List)
            .map((e) => ForecastPoint.fromJson(e))
            .toList(),
        nextPeriodForecast:
            (json['next_period_forecast'] as num?)?.toDouble(),
        confidence: (json['confidence'] as num?)?.toDouble(),
        granularity: json['granularity'] as String?,
      );
}

class ForecastSummary {
  final double currentMonthActual;
  final double currentMonthForecast;
  final double nextMonthForecast;
  final double quarterForecast;
  final double yearForecast;
  final double confidence;

  const ForecastSummary({
    required this.currentMonthActual,
    required this.currentMonthForecast,
    required this.nextMonthForecast,
    required this.quarterForecast,
    required this.yearForecast,
    required this.confidence,
  });

  factory ForecastSummary.fromJson(Map<String, dynamic> json) =>
      ForecastSummary(
        currentMonthActual:
            (json['current_month_actual'] as num).toDouble(),
        currentMonthForecast:
            (json['current_month_forecast'] as num).toDouble(),
        nextMonthForecast:
            (json['next_month_forecast'] as num).toDouble(),
        quarterForecast: (json['quarter_forecast'] as num).toDouble(),
        yearForecast: (json['year_forecast'] as num).toDouble(),
        confidence: (json['confidence'] as num).toDouble(),
      );
}
