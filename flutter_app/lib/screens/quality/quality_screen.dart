import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../providers/pipeline_provider.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class QualityScreen extends ConsumerWidget {
  const QualityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scorecard = ref.watch(qualityScorecardProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(qualityScorecardProvider),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: scorecard.when(
          loading: () => const LoadingShimmer(itemCount: 4),
          error: (e, _) => ErrorView(
            message: e.toString(),
            onRetry: () => ref.invalidate(qualityScorecardProvider),
          ),
          data: (data) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Overall score
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Row(
                    children: [
                      SizedBox(
                        width: 100,
                        height: 100,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            CircularProgressIndicator(
                              value: data.overallScore / 100,
                              strokeWidth: 8,
                              backgroundColor: Colors.grey.withOpacity(0.2),
                              color: _scoreColor(data.overallScore),
                            ),
                            Text(
                              '${data.overallScore.toStringAsFixed(0)}%',
                              style: Theme.of(context)
                                  .textTheme
                                  .headlineSmall
                                  ?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 24),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Data Quality Score',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 12),
                            _StatRow('Total Checks',
                                data.totalChecks.toString()),
                            _StatRow('Passed', data.passedChecks.toString(),
                                color: AppColors.success),
                            _StatRow('Failed', data.failedChecks.toString(),
                                color: AppColors.error),
                            _StatRow(
                                'Warnings', data.warningChecks.toString(),
                                color: AppColors.warning),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Stage scores
              Text(
                'Quality by Stage',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 8),
              ...data.stageScores.entries.map((entry) => Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: Icon(
                        _stageIcon(entry.key),
                        color: _scoreColor(entry.value),
                      ),
                      title: Text(
                        entry.key.toUpperCase(),
                        style:
                            const TextStyle(fontWeight: FontWeight.w500),
                      ),
                      trailing: Text(
                        '${entry.value.toStringAsFixed(0)}%',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 16,
                          color: _scoreColor(entry.value),
                        ),
                      ),
                      subtitle: LinearProgressIndicator(
                        value: entry.value / 100,
                        backgroundColor: Colors.grey.withOpacity(0.2),
                        color: _scoreColor(entry.value),
                      ),
                    ),
                  )),
            ],
          ),
        ),
      ),
    );
  }

  Color _scoreColor(double score) {
    if (score >= 90) return AppColors.success;
    if (score >= 70) return AppColors.warning;
    return AppColors.error;
  }

  IconData _stageIcon(String stage) {
    switch (stage.toLowerCase()) {
      case 'bronze':
        return Icons.download_rounded;
      case 'silver':
      case 'staging':
        return Icons.cleaning_services_rounded;
      case 'gold':
      case 'marts':
        return Icons.star_rounded;
      default:
        return Icons.layers_rounded;
    }
  }
}

class _StatRow extends StatelessWidget {
  final String label;
  final String value;
  final Color? color;

  const _StatRow(this.label, this.value, {this.color});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          Text(
            value,
            style: TextStyle(
              fontWeight: FontWeight.w600,
              color: color,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}
