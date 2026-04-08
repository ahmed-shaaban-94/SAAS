import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/formatters.dart';
import '../../models/target.dart';
import '../../services/targets_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';
import '../../widgets/empty_state.dart';

final targetSummaryProvider =
    FutureProvider.autoDispose<TargetSummary>((ref) async {
  final service = ref.watch(targetsServiceProvider);
  return service.getSummary();
});

class GoalsScreen extends ConsumerWidget {
  const GoalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final summary = ref.watch(targetSummaryProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(targetSummaryProvider),
      child: summary.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: LoadingShimmer(itemCount: 4),
        ),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(targetSummaryProvider),
        ),
        data: (data) => SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Overview card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(20),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Goal Progress',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '${data.achievedTargets}/${data.totalTargets} achieved',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                      SizedBox(
                        width: 72,
                        height: 72,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            CircularProgressIndicator(
                              value: data.overallAchievement / 100,
                              strokeWidth: 6,
                              backgroundColor: Colors.grey.withOpacity(0.2),
                              color: data.overallAchievement >= 100
                                  ? AppColors.success
                                  : AppColors.primary,
                            ),
                            Text(
                              '${data.overallAchievement.toStringAsFixed(0)}%',
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Target list
              if (data.targets.isEmpty)
                const EmptyState(
                  icon: Icons.flag_outlined,
                  title: 'No Goals Set',
                  subtitle: 'Create targets to track your progress',
                )
              else
                ...data.targets.map((target) => _TargetCard(target: target)),
            ],
          ),
        ),
      ),
    );
  }
}

class _TargetCard extends StatelessWidget {
  final Target target;

  const _TargetCard({required this.target});

  @override
  Widget build(BuildContext context) {
    final achievement = target.achievementPct ?? 0;
    final color = achievement >= 100
        ? AppColors.success
        : achievement >= 70
            ? AppColors.warning
            : AppColors.error;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  target.isAchieved
                      ? Icons.check_circle_rounded
                      : Icons.flag_rounded,
                  color: color,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    '${target.metric.toUpperCase()} - ${target.period}',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                Text(
                  '${achievement.toStringAsFixed(0)}%',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (achievement / 100).clamp(0.0, 1.0),
                backgroundColor: Colors.grey.withOpacity(0.2),
                color: color,
                minHeight: 6,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Actual: ${Formatters.compact(target.actualValue ?? 0)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                Text(
                  'Target: ${Formatters.compact(target.targetValue)}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
