import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/dashboard_data.dart';
import '../models/kpi_summary.dart';
import '../models/trend_result.dart';
import '../models/ranking_result.dart';
import '../models/product_performance.dart';
import '../models/customer_analytics.dart';
import '../models/staff_performance.dart';
import '../models/site_detail.dart';
import '../models/return_analysis.dart';
import '../models/filter_options.dart';

final analyticsServiceProvider = Provider<AnalyticsService>((ref) {
  return AnalyticsService(ref.watch(apiClientProvider));
});

class AnalyticsService {
  final ApiClient _api;

  AnalyticsService(this._api);

  Future<DashboardData> getDashboard({
    Map<String, dynamic>? params,
  }) async {
    return _api.get(
      '/analytics/dashboard',
      queryParameters: params,
      fromJson: (data) => DashboardData.fromJson(data),
    );
  }

  Future<KpiSummary> getSummary({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/summary',
      queryParameters: params,
      fromJson: (data) => KpiSummary.fromJson(data),
    );
  }

  Future<TrendResult> getDailyTrend({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/trends/daily',
      queryParameters: params,
      fromJson: (data) => TrendResult.fromJson(data),
    );
  }

  Future<TrendResult> getMonthlyTrend({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/trends/monthly',
      queryParameters: params,
      fromJson: (data) => TrendResult.fromJson(data),
    );
  }

  Future<RankingResult> getTopProducts({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/products/top',
      queryParameters: params,
      fromJson: (data) => RankingResult.fromJson(data),
    );
  }

  Future<RankingResult> getTopCustomers({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/customers/top',
      queryParameters: params,
      fromJson: (data) => RankingResult.fromJson(data),
    );
  }

  Future<RankingResult> getTopStaff({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/staff/top',
      queryParameters: params,
      fromJson: (data) => RankingResult.fromJson(data),
    );
  }

  Future<RankingResult> getSites({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/sites',
      queryParameters: params,
      fromJson: (data) => RankingResult.fromJson(data),
    );
  }

  Future<ProductPerformance> getProductDetail(String productKey) async {
    return _api.get(
      '/analytics/products/$productKey',
      fromJson: (data) => ProductPerformance.fromJson(data),
    );
  }

  Future<CustomerAnalytics> getCustomerDetail(String customerKey) async {
    return _api.get(
      '/analytics/customers/$customerKey',
      fromJson: (data) => CustomerAnalytics.fromJson(data),
    );
  }

  Future<StaffPerformance> getStaffDetail(String staffKey) async {
    return _api.get(
      '/analytics/staff/$staffKey',
      fromJson: (data) => StaffPerformance.fromJson(data),
    );
  }

  Future<SiteDetail> getSiteDetail(String siteKey) async {
    return _api.get(
      '/analytics/sites/$siteKey',
      fromJson: (data) => SiteDetail.fromJson(data),
    );
  }

  Future<List<ReturnItem>> getReturns({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/returns',
      queryParameters: params,
      fromJson: (data) =>
          (data as List).map((e) => ReturnItem.fromJson(e)).toList(),
    );
  }

  Future<ReturnsTrend> getReturnsTrend({Map<String, dynamic>? params}) async {
    return _api.get(
      '/analytics/returns/trend',
      queryParameters: params,
      fromJson: (data) => ReturnsTrend.fromJson(data),
    );
  }

  Future<FilterOptions> getFilterOptions() async {
    return _api.get(
      '/analytics/filters/options',
      fromJson: (data) => FilterOptions.fromJson(data),
    );
  }
}
