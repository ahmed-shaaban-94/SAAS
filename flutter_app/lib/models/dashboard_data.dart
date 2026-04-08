import 'kpi_summary.dart';
import 'trend_result.dart';
import 'ranking_result.dart';
import 'filter_options.dart';

class DashboardData {
  final KpiSummary kpi;
  final TrendResult dailyTrend;
  final TrendResult monthlyTrend;
  final RankingResult topProducts;
  final RankingResult topCustomers;
  final RankingResult topStaff;
  final FilterOptions filterOptions;

  const DashboardData({
    required this.kpi,
    required this.dailyTrend,
    required this.monthlyTrend,
    required this.topProducts,
    required this.topCustomers,
    required this.topStaff,
    required this.filterOptions,
  });

  factory DashboardData.fromJson(Map<String, dynamic> json) => DashboardData(
        kpi: KpiSummary.fromJson(json['kpi']),
        dailyTrend: TrendResult.fromJson(json['daily_trend']),
        monthlyTrend: TrendResult.fromJson(json['monthly_trend']),
        topProducts: RankingResult.fromJson(json['top_products']),
        topCustomers: RankingResult.fromJson(json['top_customers']),
        topStaff: RankingResult.fromJson(json['top_staff']),
        filterOptions: FilterOptions.fromJson(json['filter_options']),
      );
}
