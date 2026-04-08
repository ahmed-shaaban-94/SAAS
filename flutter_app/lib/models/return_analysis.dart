import 'trend_result.dart';

class ReturnItem {
  final String drugName;
  final String? brand;
  final String? customerName;
  final String? origin;
  final int returnQuantity;
  final double returnAmount;
  final int returnCount;

  const ReturnItem({
    required this.drugName,
    this.brand,
    this.customerName,
    this.origin,
    required this.returnQuantity,
    required this.returnAmount,
    required this.returnCount,
  });

  factory ReturnItem.fromJson(Map<String, dynamic> json) => ReturnItem(
        drugName: json['drug_name'] as String,
        brand: json['brand'] as String?,
        customerName: json['customer_name'] as String?,
        origin: json['origin'] as String?,
        returnQuantity: (json['return_quantity'] as num).toInt(),
        returnAmount: (json['return_amount'] as num).toDouble(),
        returnCount: (json['return_count'] as num).toInt(),
      );
}

class ReturnsTrend {
  final List<ReturnsTrendPoint> points;

  const ReturnsTrend({required this.points});

  factory ReturnsTrend.fromJson(Map<String, dynamic> json) => ReturnsTrend(
        points: (json['points'] as List)
            .map((e) => ReturnsTrendPoint.fromJson(e))
            .toList(),
      );
}

class ReturnsTrendPoint {
  final String period;
  final int returnCount;
  final double returnAmount;
  final double returnRate;

  const ReturnsTrendPoint({
    required this.period,
    required this.returnCount,
    required this.returnAmount,
    required this.returnRate,
  });

  factory ReturnsTrendPoint.fromJson(Map<String, dynamic> json) =>
      ReturnsTrendPoint(
        period: json['period'] as String,
        returnCount: (json['return_count'] as num).toInt(),
        returnAmount: (json['return_amount'] as num).toDouble(),
        returnRate: (json['return_rate'] as num).toDouble(),
      );
}
