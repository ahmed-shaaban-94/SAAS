import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../core/utils/extensions.dart';
import '../core/utils/formatters.dart';

class KpiCard extends StatelessWidget {
  final String title;
  final double value;
  final double? growthPct;
  final IconData icon;
  final String? subtitle;
  final bool isCurrency;

  const KpiCard({
    super.key,
    required this.title,
    required this.value,
    this.growthPct,
    required this.icon,
    this.subtitle,
    this.isCurrency = true,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.primary.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, color: AppColors.primary, size: 20),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: context.textTheme.bodySmall?.copyWith(
                      color: isDark ? Colors.white54 : Colors.black54,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              isCurrency ? Formatters.currency(value) : Formatters.compact(value),
              style: context.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            if (growthPct != null) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  Icon(
                    growthPct! >= 0
                        ? Icons.trending_up_rounded
                        : Icons.trending_down_rounded,
                    size: 16,
                    color: growthPct!.growthColor,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    Formatters.growth(growthPct),
                    style: context.textTheme.bodySmall?.copyWith(
                      color: growthPct!.growthColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (subtitle != null) ...[
                    const SizedBox(width: 4),
                    Text(
                      subtitle!,
                      style: context.textTheme.bodySmall?.copyWith(
                        color: isDark ? Colors.white38 : Colors.black38,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
