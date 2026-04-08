import 'trend_result.dart';

class CustomerAnalytics {
  final String customerKey;
  final String? customerId;
  final String customerName;
  final double totalAmount;
  final double netAmount;
  final int transactionCount;
  final int uniqueProducts;
  final int returnCount;
  final double returnRate;
  final double avgTransactionValue;
  final List<TimeSeriesPoint> monthlyTrend;

  const CustomerAnalytics({
    required this.customerKey,
    this.customerId,
    required this.customerName,
    required this.totalAmount,
    required this.netAmount,
    required this.transactionCount,
    required this.uniqueProducts,
    required this.returnCount,
    required this.returnRate,
    required this.avgTransactionValue,
    required this.monthlyTrend,
  });

  factory CustomerAnalytics.fromJson(Map<String, dynamic> json) =>
      CustomerAnalytics(
        customerKey: json['customer_key'] as String,
        customerId: json['customer_id'] as String?,
        customerName: json['customer_name'] as String,
        totalAmount: (json['total_amount'] as num).toDouble(),
        netAmount: (json['net_amount'] as num).toDouble(),
        transactionCount: (json['transaction_count'] as num).toInt(),
        uniqueProducts: (json['unique_products'] as num).toInt(),
        returnCount: (json['return_count'] as num).toInt(),
        returnRate: (json['return_rate'] as num?)?.toDouble() ?? 0,
        avgTransactionValue:
            (json['avg_transaction_value'] as num?)?.toDouble() ?? 0,
        monthlyTrend: (json['monthly_trend'] as List?)
                ?.map((e) => TimeSeriesPoint.fromJson(e))
                .toList() ??
            [],
      );
}
