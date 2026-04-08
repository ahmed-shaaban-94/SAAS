import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../core/utils/extensions.dart';
import '../models/trend_result.dart';

class TrendChart extends StatelessWidget {
  final TrendResult data;
  final String title;
  final bool showDots;
  final double height;

  const TrendChart({
    super.key,
    required this.data,
    required this.title,
    this.showDots = false,
    this.height = 220,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final gridColor = isDark ? Colors.white10 : Colors.black08;
    final labelColor = isDark ? Colors.white38 : Colors.black38;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: context.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (data.growthPct != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: data.growthPct!.growthColor.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '${data.growthPct!.growthSign}${data.growthPct!.toStringAsFixed(1)}%',
                      style: context.textTheme.labelSmall?.copyWith(
                        color: data.growthPct!.growthColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: height,
              child: data.points.isEmpty
                  ? const Center(child: Text('No data'))
                  : LineChart(
                      LineChartData(
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: false,
                          horizontalInterval: _calcInterval(),
                          getDrawingHorizontalLine: (value) => FlLine(
                            color: gridColor,
                            strokeWidth: 1,
                          ),
                        ),
                        titlesData: FlTitlesData(
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 50,
                              getTitlesWidget: (value, meta) => Text(
                                value.asCurrency,
                                style: TextStyle(
                                  fontSize: 10,
                                  color: labelColor,
                                ),
                              ),
                            ),
                          ),
                          bottomTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              interval: _xInterval(),
                              getTitlesWidget: (value, meta) {
                                final idx = value.toInt();
                                if (idx < 0 || idx >= data.points.length) {
                                  return const SizedBox();
                                }
                                return Padding(
                                  padding: const EdgeInsets.only(top: 8),
                                  child: Text(
                                    _shortenLabel(data.points[idx].period),
                                    style: TextStyle(
                                      fontSize: 9,
                                      color: labelColor,
                                    ),
                                  ),
                                );
                              },
                            ),
                          ),
                          topTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false)),
                          rightTitles: const AxisTitles(
                              sideTitles: SideTitles(showTitles: false)),
                        ),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            spots: data.points.asMap().entries.map((e) {
                              return FlSpot(
                                  e.key.toDouble(), e.value.value);
                            }).toList(),
                            isCurved: true,
                            curveSmoothness: 0.3,
                            color: AppColors.primary,
                            barWidth: 2.5,
                            dotData: FlDotData(show: showDots),
                            belowBarData: BarAreaData(
                              show: true,
                              color: AppColors.primary.withOpacity(0.08),
                            ),
                          ),
                        ],
                        lineTouchData: LineTouchData(
                          touchTooltipData: LineTouchTooltipData(
                            getTooltipItems: (spots) {
                              return spots.map((spot) {
                                final point = data.points[spot.x.toInt()];
                                return LineTooltipItem(
                                  '${point.period}\n${spot.y.asCurrency}',
                                  TextStyle(
                                    color: Colors.white,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                );
                              }).toList();
                            },
                          ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  double _calcInterval() {
    if (data.points.isEmpty) return 1;
    final range = data.maximum - data.minimum;
    if (range == 0) return 1;
    return range / 4;
  }

  double _xInterval() {
    final len = data.points.length;
    if (len <= 7) return 1;
    if (len <= 15) return 2;
    if (len <= 31) return 5;
    return (len / 6).ceilToDouble();
  }

  String _shortenLabel(String label) {
    if (label.length <= 5) return label;
    // e.g. 2024-01-15 => 01/15
    if (label.contains('-') && label.length >= 10) {
      return label.substring(5).replaceAll('-', '/');
    }
    return label;
  }
}
