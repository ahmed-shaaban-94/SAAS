import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/trend_result.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/trend_chart.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class StaffDetailScreen extends ConsumerWidget {
  final String staffKey;

  const StaffDetailScreen({super.key, required this.staffKey});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(staffDetailProvider(staffKey));

    return detail.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 4),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(staffDetailProvider(staffKey)),
      ),
      data: (staff) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              staff.staffName,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            if (staff.position != null)
              Text(
                staff.position!,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
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
                  title: 'Net Revenue',
                  value: staff.totalNetAmount,
                  icon: Icons.attach_money_rounded,
                ),
                KpiCard(
                  title: 'Transactions',
                  value: staff.transactionCount.toDouble(),
                  icon: Icons.receipt_rounded,
                  isCurrency: false,
                ),
                KpiCard(
                  title: 'Avg Transaction',
                  value: staff.avgTransactionValue,
                  icon: Icons.analytics_rounded,
                ),
                KpiCard(
                  title: 'Unique Customers',
                  value: staff.uniqueCustomers.toDouble(),
                  icon: Icons.people_rounded,
                  isCurrency: false,
                ),
              ],
            ),
            const SizedBox(height: 20),

            if (staff.monthlyTrend.isNotEmpty)
              TrendChart(
                data: TrendResult(
                  points: staff.monthlyTrend,
                  total: staff.totalNetAmount,
                  average: staff.totalNetAmount /
                      (staff.monthlyTrend.isNotEmpty
                          ? staff.monthlyTrend.length
                          : 1),
                  minimum: staff.monthlyTrend
                      .map((p) => p.value)
                      .reduce((a, b) => a < b ? a : b),
                  maximum: staff.monthlyTrend
                      .map((p) => p.value)
                      .reduce((a, b) => a > b ? a : b),
                ),
                title: 'Monthly Revenue Trend',
                showDots: true,
              ),
          ],
        ),
      ),
    );
  }
}
