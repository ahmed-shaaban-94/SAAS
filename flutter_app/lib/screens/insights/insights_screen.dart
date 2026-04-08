import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/extensions.dart';
import '../../models/ai_summary.dart';
import '../../services/ai_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

final aiAvailableProvider = FutureProvider.autoDispose<bool>((ref) async {
  final service = ref.watch(aiServiceProvider);
  return service.checkAvailability();
});

final aiSummaryProvider =
    FutureProvider.autoDispose<AiSummary>((ref) async {
  final service = ref.watch(aiServiceProvider);
  return service.getSummary();
});

final aiAnomaliesProvider =
    FutureProvider.autoDispose<AnomalyReport>((ref) async {
  final service = ref.watch(aiServiceProvider);
  return service.getAnomalies();
});

class InsightsScreen extends ConsumerWidget {
  const InsightsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final available = ref.watch(aiAvailableProvider);
    final summary = ref.watch(aiSummaryProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(aiSummaryProvider);
        ref.invalidate(aiAnomaliesProvider);
      },
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppColors.accent.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.auto_awesome_rounded,
                    color: AppColors.accent,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'AI Insights',
                        style: context.textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Powered by AI analysis',
                        style: context.textTheme.bodySmall?.copyWith(
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                ),
                available.when(
                  data: (isAvailable) => Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: (isAvailable ? AppColors.success : AppColors.error)
                          .withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      isAvailable ? 'ACTIVE' : 'OFFLINE',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color:
                            isAvailable ? AppColors.success : AppColors.error,
                      ),
                    ),
                  ),
                  loading: () => const SizedBox(),
                  error: (_, __) => const SizedBox(),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Executive Summary
            summary.when(
              loading: () => const LoadingShimmer(itemCount: 3),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (data) => Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Narrative
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.summarize_rounded, size: 18),
                              const SizedBox(width: 8),
                              Text(
                                'Executive Summary',
                                style:
                                    context.textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),
                          Text(
                            data.narrative,
                            style: context.textTheme.bodyMedium?.copyWith(
                              height: 1.6,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Key Insights
                  if (data.keyInsights.isNotEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.lightbulb_rounded,
                                    size: 18, color: AppColors.accent),
                                const SizedBox(width: 8),
                                Text(
                                  'Key Insights',
                                  style: context.textTheme.titleSmall
                                      ?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            ...data.keyInsights.map((insight) => Padding(
                                  padding:
                                      const EdgeInsets.only(bottom: 8),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      const Padding(
                                        padding: EdgeInsets.only(top: 6),
                                        child: Icon(
                                          Icons.circle,
                                          size: 6,
                                          color: AppColors.primary,
                                        ),
                                      ),
                                      const SizedBox(width: 10),
                                      Expanded(
                                        child: Text(
                                          insight,
                                          style: context
                                              .textTheme.bodyMedium
                                              ?.copyWith(height: 1.5),
                                        ),
                                      ),
                                    ],
                                  ),
                                )),
                          ],
                        ),
                      ),
                    ),
                  const SizedBox(height: 12),

                  // Recommendations
                  if (data.recommendations.isNotEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.tips_and_updates_rounded,
                                    size: 18, color: AppColors.secondary),
                                const SizedBox(width: 8),
                                Text(
                                  'Recommendations',
                                  style: context.textTheme.titleSmall
                                      ?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 12),
                            ...data.recommendations
                                .asMap()
                                .entries
                                .map((entry) => Padding(
                                      padding:
                                          const EdgeInsets.only(bottom: 8),
                                      child: Row(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          CircleAvatar(
                                            radius: 10,
                                            backgroundColor: AppColors
                                                .secondary
                                                .withOpacity(0.1),
                                            child: Text(
                                              '${entry.key + 1}',
                                              style: const TextStyle(
                                                fontSize: 10,
                                                fontWeight: FontWeight.w600,
                                                color: AppColors.secondary,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(width: 10),
                                          Expanded(
                                            child: Text(
                                              entry.value,
                                              style: context
                                                  .textTheme.bodyMedium
                                                  ?.copyWith(height: 1.5),
                                            ),
                                          ),
                                        ],
                                      ),
                                    )),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
