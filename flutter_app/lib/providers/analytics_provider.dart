import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/ranking_result.dart';
import '../models/product_performance.dart';
import '../models/customer_analytics.dart';
import '../models/staff_performance.dart';
import '../models/site_detail.dart';
import '../models/return_analysis.dart';
import '../services/analytics_service.dart';
import 'dashboard_provider.dart';

// Products
final topProductsProvider =
    FutureProvider.autoDispose<RankingResult>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getTopProducts(params: filter.toQueryParams());
});

final productDetailProvider =
    FutureProvider.autoDispose.family<ProductPerformance, String>(
        (ref, productKey) async {
  final service = ref.watch(analyticsServiceProvider);
  return service.getProductDetail(productKey);
});

// Customers
final topCustomersProvider =
    FutureProvider.autoDispose<RankingResult>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getTopCustomers(params: filter.toQueryParams());
});

final customerDetailProvider =
    FutureProvider.autoDispose.family<CustomerAnalytics, String>(
        (ref, customerKey) async {
  final service = ref.watch(analyticsServiceProvider);
  return service.getCustomerDetail(customerKey);
});

// Staff
final topStaffProvider =
    FutureProvider.autoDispose<RankingResult>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getTopStaff(params: filter.toQueryParams());
});

final staffDetailProvider =
    FutureProvider.autoDispose.family<StaffPerformance, String>(
        (ref, staffKey) async {
  final service = ref.watch(analyticsServiceProvider);
  return service.getStaffDetail(staffKey);
});

// Sites
final sitesProvider =
    FutureProvider.autoDispose<RankingResult>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getSites(params: filter.toQueryParams());
});

final siteDetailProvider =
    FutureProvider.autoDispose.family<SiteDetail, String>(
        (ref, siteKey) async {
  final service = ref.watch(analyticsServiceProvider);
  return service.getSiteDetail(siteKey);
});

// Returns
final returnsProvider =
    FutureProvider.autoDispose<List<ReturnItem>>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getReturns(params: filter.toQueryParams());
});

final returnsTrendProvider =
    FutureProvider.autoDispose<ReturnsTrend>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getReturnsTrend(params: filter.toQueryParams());
});
