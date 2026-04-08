import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/formatters.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class SiteDetailScreen extends ConsumerWidget {
  final String siteKey;

  const SiteDetailScreen({super.key, required this.siteKey});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(siteDetailProvider(siteKey));

    return detail.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 4),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(siteDetailProvider(siteKey)),
      ),
      data: (site) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              site.siteName,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            Text(
              'Code: ${site.siteCode}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            const SizedBox(height: 20),

            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.6,
              children: [
                KpiCard(
                  title: 'Revenue',
                  value: site.totalRevenue,
                  icon: Icons.attach_money_rounded,
                ),
                KpiCard(
                  title: 'Transactions',
                  value: site.transactionCount.toDouble(),
                  icon: Icons.receipt_rounded,
                  isCurrency: false,
                ),
                KpiCard(
                  title: 'Customers',
                  value: site.uniqueCustomers.toDouble(),
                  icon: Icons.people_rounded,
                  isCurrency: false,
                ),
                KpiCard(
                  title: 'Avg Transaction',
                  value: site.avgTransactionValue,
                  icon: Icons.analytics_rounded,
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Customer Type Breakdown
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Customer Type Mix',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                    const SizedBox(height: 16),
                    SizedBox(
                      height: 180,
                      child: PieChart(
                        PieChartData(
                          sections: [
                            PieChartSectionData(
                              value: site.walkInRatio * 100,
                              title:
                                  'Walk-in\n${(site.walkInRatio * 100).toStringAsFixed(0)}%',
                              color: AppColors.primary,
                              radius: 60,
                              titleStyle: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                            PieChartSectionData(
                              value: site.insuranceRatio * 100,
                              title:
                                  'Insurance\n${(site.insuranceRatio * 100).toStringAsFixed(0)}%',
                              color: AppColors.secondary,
                              radius: 60,
                              titleStyle: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: Colors.white,
                              ),
                            ),
                          ],
                          sectionsSpace: 2,
                          centerSpaceRadius: 30,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
