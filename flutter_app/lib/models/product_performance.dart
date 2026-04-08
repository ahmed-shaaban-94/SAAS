import 'trend_result.dart';

class ProductPerformance {
  final String productKey;
  final String? drugCode;
  final String drugName;
  final String? brand;
  final String? category;
  final int totalQuantity;
  final double totalSales;
  final double totalReturns;
  final double netSales;
  final int uniqueCustomers;
  final List<TimeSeriesPoint> monthlyTrend;

  const ProductPerformance({
    required this.productKey,
    this.drugCode,
    required this.drugName,
    this.brand,
    this.category,
    required this.totalQuantity,
    required this.totalSales,
    required this.totalReturns,
    required this.netSales,
    required this.uniqueCustomers,
    required this.monthlyTrend,
  });

  factory ProductPerformance.fromJson(Map<String, dynamic> json) =>
      ProductPerformance(
        productKey: json['product_key'] as String,
        drugCode: json['drug_code'] as String?,
        drugName: json['drug_name'] as String,
        brand: json['brand'] as String?,
        category: json['category'] as String?,
        totalQuantity: (json['total_quantity'] as num).toInt(),
        totalSales: (json['total_sales'] as num).toDouble(),
        totalReturns: (json['total_returns'] as num).toDouble(),
        netSales: (json['net_sales'] as num).toDouble(),
        uniqueCustomers: (json['unique_customers'] as num).toInt(),
        monthlyTrend: (json['monthly_trend'] as List?)
                ?.map((e) => TimeSeriesPoint.fromJson(e))
                .toList() ??
            [],
      );
}
