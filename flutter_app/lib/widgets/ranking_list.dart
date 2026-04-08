import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../core/utils/extensions.dart';
import '../core/utils/formatters.dart';
import '../models/ranking_result.dart';

class RankingList extends StatelessWidget {
  final RankingResult data;
  final String title;
  final void Function(RankingItem)? onItemTap;
  final int maxItems;

  const RankingList({
    super.key,
    required this.data,
    required this.title,
    this.onItemTap,
    this.maxItems = 10,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;
    final items = data.items.take(maxItems).toList();

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
                Text(
                  'Total: ${Formatters.compact(data.total)}',
                  style: context.textTheme.bodySmall?.copyWith(
                    color: isDark ? Colors.white38 : Colors.black38,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ...items.map((item) => _RankingRow(
                  item: item,
                  onTap: onItemTap != null ? () => onItemTap!(item) : null,
                )),
          ],
        ),
      ),
    );
  }
}

class _RankingRow extends StatelessWidget {
  final RankingItem item;
  final VoidCallback? onTap;

  const _RankingRow({required this.item, this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = context.isDark;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            // Rank badge
            Container(
              width: 28,
              height: 28,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: item.rank <= 3
                    ? AppColors.primary.withOpacity(0.1)
                    : (isDark ? Colors.white10 : Colors.black06),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                '${item.rank}',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: item.rank <= 3 ? AppColors.primary : null,
                ),
              ),
            ),
            const SizedBox(width: 12),
            // Name
            Expanded(
              child: Text(
                item.name,
                style: context.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w500,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(width: 8),
            // Value
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  Formatters.compact(item.value),
                  style: context.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  '${item.pctOfTotal.toStringAsFixed(1)}%',
                  style: context.textTheme.bodySmall?.copyWith(
                    color: isDark ? Colors.white38 : Colors.black38,
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
