import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/utils/extensions.dart';
import '../../providers/dashboard_provider.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/trend_chart.dart';
import '../../widgets/ranking_list.dart';
import '../../widgets/filter_bar.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboard = ref.watch(dashboardProvider);

    return dashboard.when(
      loading: () => const SingleChildScrollView(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 6, height: 120),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(dashboardProvider),
      ),
      data: (data) => RefreshIndicator(
        onRefresh: () async => ref.invalidate(dashboardProvider),
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 8),
              FilterBar(options: data.filterOptions),
              const SizedBox(height: 16),

              // KPI Cards
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final crossAxisCount = context.isMobile ? 2 : 4;
                    return GridView.count(
                      crossAxisCount: crossAxisCount,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 12,
                      crossAxisSpacing: 12,
                      childAspectRatio: context.isMobile ? 1.3 : 1.6,
                      children: [
                        KpiCard(
                          title: 'Today',
                          value: data.kpi.todayGross,
                          growthPct: data.kpi.todayGrowth,
                          icon: Icons.today_rounded,
                          subtitle: 'vs yesterday',
                        ),
                        KpiCard(
                          title: 'MTD',
                          value: data.kpi.mtdGross,
                          growthPct: data.kpi.mtdGrowth,
                          icon: Icons.calendar_month_rounded,
                        ),
                        KpiCard(
                          title: 'Transactions',
                          value: data.kpi.mtdTransactions.toDouble(),
                          icon: Icons.receipt_long_rounded,
                          isCurrency: false,
                        ),
                        KpiCard(
                          title: 'Customers',
                          value: data.kpi.mtdCustomers.toDouble(),
                          icon: Icons.people_rounded,
                          isCurrency: false,
                        ),
                      ],
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),

              // Trend charts
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TrendChart(
                  data: data.dailyTrend,
                  title: 'Daily Revenue Trend',
                ),
              ),
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: TrendChart(
                  data: data.monthlyTrend,
                  title: 'Monthly Revenue Trend',
                  showDots: true,
                ),
              ),
              const SizedBox(height: 16),

              // Rankings
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: context.isMobile
                    ? Column(
                        children: [
                          RankingList(
                            data: data.topProducts,
                            title: 'Top Products',
                            maxItems: 5,
                            onItemTap: (item) =>
                                context.go('/products/${item.key}'),
                          ),
                          const SizedBox(height: 12),
                          RankingList(
                            data: data.topCustomers,
                            title: 'Top Customers',
                            maxItems: 5,
                            onItemTap: (item) =>
                                context.go('/customers/${item.key}'),
                          ),
                          const SizedBox(height: 12),
                          RankingList(
                            data: data.topStaff,
                            title: 'Top Staff',
                            maxItems: 5,
                            onItemTap: (item) =>
                                context.go('/staff/${item.key}'),
                          ),
                        ],
                      )
                    : Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: RankingList(
                              data: data.topProducts,
                              title: 'Top Products',
                              maxItems: 5,
                              onItemTap: (item) =>
                                  context.go('/products/${item.key}'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: RankingList(
                              data: data.topCustomers,
                              title: 'Top Customers',
                              maxItems: 5,
                              onItemTap: (item) =>
                                  context.go('/customers/${item.key}'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: RankingList(
                              data: data.topStaff,
                              title: 'Top Staff',
                              maxItems: 5,
                              onItemTap: (item) =>
                                  context.go('/staff/${item.key}'),
                            ),
                          ),
                        ],
                      ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
