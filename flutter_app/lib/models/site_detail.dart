class SiteDetail {
  final String siteKey;
  final String siteCode;
  final String siteName;
  final double totalRevenue;
  final int transactionCount;
  final int uniqueCustomers;
  final double avgTransactionValue;
  final double walkInRatio;
  final double insuranceRatio;
  final double returnRate;

  const SiteDetail({
    required this.siteKey,
    required this.siteCode,
    required this.siteName,
    required this.totalRevenue,
    required this.transactionCount,
    required this.uniqueCustomers,
    required this.avgTransactionValue,
    required this.walkInRatio,
    required this.insuranceRatio,
    required this.returnRate,
  });

  factory SiteDetail.fromJson(Map<String, dynamic> json) => SiteDetail(
        siteKey: json['site_key'] as String,
        siteCode: json['site_code'] as String,
        siteName: json['site_name'] as String,
        totalRevenue: (json['total_revenue'] as num).toDouble(),
        transactionCount: (json['transaction_count'] as num).toInt(),
        uniqueCustomers: (json['unique_customers'] as num).toInt(),
        avgTransactionValue:
            (json['avg_transaction_value'] as num).toDouble(),
        walkInRatio: (json['walk_in_ratio'] as num?)?.toDouble() ?? 0,
        insuranceRatio: (json['insurance_ratio'] as num?)?.toDouble() ?? 0,
        returnRate: (json['return_rate'] as num?)?.toDouble() ?? 0,
      );
}
