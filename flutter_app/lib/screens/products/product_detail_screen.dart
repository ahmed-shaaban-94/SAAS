import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/utils/formatters.dart';
import '../../models/trend_result.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/kpi_card.dart';
import '../../widgets/trend_chart.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class ProductDetailScreen extends ConsumerWidget {
  final String productKey;

  const ProductDetailScreen({super.key, required this.productKey});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(productDetailProvider(productKey));

    return detail.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 4),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(productDetailProvider(productKey)),
      ),
      data: (product) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Text(
              product.drugName,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
            ),
            if (product.brand != null || product.category != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Wrap(
                  spacing: 8,
                  children: [
                    if (product.brand != null)
                      Chip(
                        label: Text(product.brand!,
                            style: const TextStyle(fontSize: 12)),
                        visualDensity:
                            const VisualDensity(vertical: -3),
                      ),
                    if (product.category != null)
                      Chip(
                        label: Text(product.category!,
                            style: const TextStyle(fontSize: 12)),
                        visualDensity:
                            const VisualDensity(vertical: -3),
                      ),
                  ],
                ),
              ),
            const SizedBox(height: 20),

            // KPIs
            GridView.count(
              crossAxisCount: 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              childAspectRatio: 1.6,
              children: [
                KpiCard(
                  title: 'Net Sales',
                  value: product.netSales,
                  icon: Icons.attach_money_rounded,
                ),
                KpiCard(
                  title: 'Total Quantity',
                  value: product.totalQuantity.toDouble(),
                  icon: Icons.inventory_rounded,
                  isCurrency: false,
                ),
                KpiCard(
                  title: 'Returns',
                  value: product.totalReturns,
                  icon: Icons.assignment_return_rounded,
                ),
                KpiCard(
                  title: 'Customers',
                  value: product.uniqueCustomers.toDouble(),
                  icon: Icons.people_rounded,
                  isCurrency: false,
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Monthly trend
            if (product.monthlyTrend.isNotEmpty)
              TrendChart(
                data: TrendResult(
                  points: product.monthlyTrend,
                  total: product.netSales,
                  average: product.netSales /
                      (product.monthlyTrend.length > 0
                          ? product.monthlyTrend.length
                          : 1),
                  minimum: product.monthlyTrend
                      .map((p) => p.value)
                      .reduce((a, b) => a < b ? a : b),
                  maximum: product.monthlyTrend
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
