import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/dashboard_data.dart';
import '../models/filter_options.dart';
import '../services/analytics_service.dart';

final filterProvider = StateProvider<AnalyticsFilter>((ref) {
  return const AnalyticsFilter();
});

final dashboardProvider =
    FutureProvider.autoDispose<DashboardData>((ref) async {
  final filter = ref.watch(filterProvider);
  final service = ref.watch(analyticsServiceProvider);
  return service.getDashboard(params: filter.toQueryParams());
});
