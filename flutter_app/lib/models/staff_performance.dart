import 'trend_result.dart';

class StaffPerformance {
  final String staffKey;
  final String? staffId;
  final String staffName;
  final String? position;
  final double totalNetAmount;
  final int transactionCount;
  final double avgTransactionValue;
  final int uniqueCustomers;
  final List<TimeSeriesPoint> monthlyTrend;

  const StaffPerformance({
    required this.staffKey,
    this.staffId,
    required this.staffName,
    this.position,
    required this.totalNetAmount,
    required this.transactionCount,
    required this.avgTransactionValue,
    required this.uniqueCustomers,
    required this.monthlyTrend,
  });

  factory StaffPerformance.fromJson(Map<String, dynamic> json) =>
      StaffPerformance(
        staffKey: json['staff_key'] as String,
        staffId: json['staff_id'] as String?,
        staffName: json['staff_name'] as String,
        position: json['position'] as String?,
        totalNetAmount: (json['total_net_amount'] as num).toDouble(),
        transactionCount: (json['transaction_count'] as num).toInt(),
        avgTransactionValue:
            (json['avg_transaction_value'] as num).toDouble(),
        uniqueCustomers: (json['unique_customers'] as num).toInt(),
        monthlyTrend: (json['monthly_trend'] as List?)
                ?.map((e) => TimeSeriesPoint.fromJson(e))
                .toList() ??
            [],
      );
}
