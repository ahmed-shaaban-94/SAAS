import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/trend_result.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/trend_chart.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class CustomerDetailScreen extends ConsumerWidget {
  final String customerKey;

  const CustomerDetailScreen({super.key, required this.customerKey});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(customerDetailProvider(customerKey));

    return detail.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 4),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(customerDetailProvider(customerKey)),
      ),
      data: (customer) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              customer.customerName,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            if (customer.customerId != null)
              Text(
                'ID: ${customer.customerId}',
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
                  title: 'Net Amount',
                  value: customer.netAmount,
                  icon: Icons.attach_money_rounded,
                ),
                KpiCard(
                  title: 'Transactions',
                  value: customer.transactionCount.toDouble(),
                  icon: Icons.receipt_rounded,
                  isCurrency: false,
                ),
                KpiCard(
                  title: 'Avg Transaction',
                  value: customer.avgTransactionValue,
                  icon: Icons.analytics_rounded,
                ),
                KpiCard(
                  title: 'Return Rate',
                  value: customer.returnRate,
                  icon: Icons.assignment_return_rounded,
                  isCurrency: false,
                ),
              ],
            ),
            const SizedBox(height: 20),

            if (customer.monthlyTrend.isNotEmpty)
              TrendChart(
                data: TrendResult(
                  points: customer.monthlyTrend,
                  total: customer.netAmount,
                  average: customer.netAmount /
                      (customer.monthlyTrend.isNotEmpty
                          ? customer.monthlyTrend.length
                          : 1),
                  minimum: customer.monthlyTrend
                      .map((p) => p.value)
                      .reduce((a, b) => a < b ? a : b),
                  maximum: customer.monthlyTrend
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
