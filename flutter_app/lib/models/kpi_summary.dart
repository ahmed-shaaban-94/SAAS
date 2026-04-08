class KpiSummary {
  final double todayGross;
  final double todayGrowth;
  final double mtdGross;
  final double mtdGrowth;
  final double ytdGross;
  final double ytdGrowth;
  final int todayTransactions;
  final int mtdTransactions;
  final int ytdTransactions;
  final int todayCustomers;
  final int mtdCustomers;
  final int ytdCustomers;
  final double todayBasketSize;
  final double mtdBasketSize;
  final double ytdBasketSize;

  const KpiSummary({
    required this.todayGross,
    required this.todayGrowth,
    required this.mtdGross,
    required this.mtdGrowth,
    required this.ytdGross,
    required this.ytdGrowth,
    required this.todayTransactions,
    required this.mtdTransactions,
    required this.ytdTransactions,
    required this.todayCustomers,
    required this.mtdCustomers,
    required this.ytdCustomers,
    required this.todayBasketSize,
    required this.mtdBasketSize,
    required this.ytdBasketSize,
  });

  factory KpiSummary.fromJson(Map<String, dynamic> json) => KpiSummary(
        todayGross: (json['today_gross'] as num?)?.toDouble() ?? 0,
        todayGrowth: (json['today_growth'] as num?)?.toDouble() ?? 0,
        mtdGross: (json['mtd_gross'] as num?)?.toDouble() ?? 0,
        mtdGrowth: (json['mtd_growth'] as num?)?.toDouble() ?? 0,
        ytdGross: (json['ytd_gross'] as num?)?.toDouble() ?? 0,
        ytdGrowth: (json['ytd_growth'] as num?)?.toDouble() ?? 0,
        todayTransactions: (json['today_transactions'] as num?)?.toInt() ?? 0,
        mtdTransactions: (json['mtd_transactions'] as num?)?.toInt() ?? 0,
        ytdTransactions: (json['ytd_transactions'] as num?)?.toInt() ?? 0,
        todayCustomers: (json['today_customers'] as num?)?.toInt() ?? 0,
        mtdCustomers: (json['mtd_customers'] as num?)?.toInt() ?? 0,
        ytdCustomers: (json['ytd_customers'] as num?)?.toInt() ?? 0,
        todayBasketSize: (json['today_basket_size'] as num?)?.toDouble() ?? 0,
        mtdBasketSize: (json['mtd_basket_size'] as num?)?.toDouble() ?? 0,
        ytdBasketSize: (json['ytd_basket_size'] as num?)?.toDouble() ?? 0,
      );
}
