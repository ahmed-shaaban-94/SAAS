import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/extensions.dart';
import '../../core/utils/formatters.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class ReturnsScreen extends ConsumerWidget {
  const ReturnsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final returns = ref.watch(returnsProvider);
    final trend = ref.watch(returnsTrendProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(returnsProvider);
        ref.invalidate(returnsTrendProvider);
      },
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Trend chart
            trend.when(
              loading: () => const ShimmerCard(height: 250),
              error: (e, _) => const SizedBox(),
              data: (trendData) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Returns Trend',
                        style: context.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        height: 200,
                        child: BarChart(
                          BarChartData(
                            barGroups: trendData.points
                                .asMap()
                                .entries
                                .map((e) => BarChartGroupData(
                                      x: e.key,
                                      barRods: [
                                        BarChartRodData(
                                          toY: e.value.returnAmount,
                                          color: AppColors.error
                                              .withOpacity(0.7),
                                          width: 16,
                                          borderRadius:
                                              const BorderRadius.vertical(
                                            top: Radius.circular(4),
                                          ),
                                        ),
                                      ],
                                    ))
                                .toList(),
                            gridData: const FlGridData(
                                drawVerticalLine: false),
                            borderData: FlBorderData(show: false),
                            titlesData: FlTitlesData(
                              leftTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: false),
                              ),
                              topTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: false),
                              ),
                              rightTitles: const AxisTitles(
                                sideTitles: SideTitles(showTitles: false),
                              ),
                              bottomTitles: AxisTitles(
                                sideTitles: SideTitles(
                                  showTitles: true,
                                  getTitlesWidget: (value, meta) {
                                    final idx = value.toInt();
                                    if (idx >= trendData.points.length) {
                                      return const SizedBox();
                                    }
                                    return Text(
                                      trendData.points[idx].period
                                          .substring(5),
                                      style: const TextStyle(fontSize: 9),
                                    );
                                  },
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Returns list
            Text(
              'Top Returns',
              style: context.textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            returns.when(
              loading: () => const LoadingShimmer(itemCount: 6, height: 72),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (items) => ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final item = items[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      title: Text(
                        item.drugName,
                        style: const TextStyle(fontWeight: FontWeight.w500),
                      ),
                      subtitle: Text(
                        [
                          if (item.brand != null) item.brand,
                          '${item.returnCount} returns',
                        ].join(' - '),
                      ),
                      trailing: Text(
                        Formatters.currency(item.returnAmount),
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.error,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ShimmerCard extends StatelessWidget {
  final double height;

  const ShimmerCard({super.key, required this.height});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        height: height,
        child: const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}
