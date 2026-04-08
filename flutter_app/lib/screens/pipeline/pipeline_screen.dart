import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/formatters.dart';
import '../../models/pipeline_run.dart';
import '../../providers/pipeline_provider.dart';
import '../../services/pipeline_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';
import '../../widgets/status_badge.dart';

class PipelineScreen extends ConsumerWidget {
  const PipelineScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final runs = ref.watch(pipelineRunsProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(pipelineRunsProvider),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Trigger button
            Row(
              children: [
                Text(
                  'Pipeline Runs',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const Spacer(),
                FilledButton.icon(
                  onPressed: () async {
                    try {
                      final service = ref.read(pipelineServiceProvider);
                      await service.triggerPipeline();
                      ref.invalidate(pipelineRunsProvider);
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Pipeline triggered!'),
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Failed: $e'),
                            backgroundColor: AppColors.error,
                            behavior: SnackBarBehavior.floating,
                          ),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.play_arrow_rounded, size: 18),
                  label: const Text('Trigger'),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Runs list
            runs.when(
              loading: () => const LoadingShimmer(itemCount: 5, height: 80),
              error: (e, _) => ErrorView(
                message: e.toString(),
                onRetry: () => ref.invalidate(pipelineRunsProvider),
              ),
              data: (data) => data.items.isEmpty
                  ? const Center(
                      child: Padding(
                        padding: EdgeInsets.all(40),
                        child: Text('No pipeline runs yet'),
                      ),
                    )
                  : ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: data.items.length,
                      itemBuilder: (context, index) =>
                          _RunCard(run: data.items[index]),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RunCard extends StatelessWidget {
  final PipelineRun run;

  const _RunCard({required this.run});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                StatusBadge(status: run.status),
                const Spacer(),
                Text(
                  Formatters.date(run.startedAt),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                if (run.stage != null) ...[
                  Icon(Icons.layers_rounded, size: 14, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    run.stage!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(width: 16),
                ],
                if (run.rowsProcessed != null) ...[
                  Icon(Icons.table_rows_rounded,
                      size: 14, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    '${Formatters.integer(run.rowsProcessed)} rows',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(width: 16),
                ],
                if (run.durationSeconds != null) ...[
                  Icon(Icons.timer_rounded, size: 14, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    '${run.durationSeconds!.toStringAsFixed(1)}s',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ],
            ),
            if (run.errorMessage != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  run.errorMessage!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.error,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
