import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/formatters.dart';
import '../../models/anomaly_alert.dart';
import '../../services/anomaly_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';
import '../../widgets/empty_state.dart';

final activeAlertsProvider =
    FutureProvider.autoDispose<List<AnomalyAlert>>((ref) async {
  final service = ref.watch(anomalyServiceProvider);
  return service.getActiveAlerts();
});

class AlertsScreen extends ConsumerWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerts = ref.watch(activeAlertsProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(activeAlertsProvider),
      child: alerts.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: LoadingShimmer(itemCount: 5, height: 80),
        ),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(activeAlertsProvider),
        ),
        data: (items) => items.isEmpty
            ? const EmptyState(
                icon: Icons.check_circle_outlined,
                title: 'No Active Alerts',
                subtitle: 'All metrics are within normal ranges',
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final alert = items[index];
                  return _AlertCard(
                    alert: alert,
                    onAcknowledge: () async {
                      final service = ref.read(anomalyServiceProvider);
                      await service.acknowledgeAlert(alert.id);
                      ref.invalidate(activeAlertsProvider);
                    },
                  );
                },
              ),
      ),
    );
  }
}

class _AlertCard extends StatelessWidget {
  final AnomalyAlert alert;
  final VoidCallback onAcknowledge;

  const _AlertCard({required this.alert, required this.onAcknowledge});

  @override
  Widget build(BuildContext context) {
    final severityColor = _severityColor(alert.severity);

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: severityColor.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    alert.severity.toUpperCase(),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: severityColor,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    alert.metric,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                Text(
                  Formatters.date(alert.detectedAt),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${alert.dimensionValue} - Expected: ${Formatters.compact(alert.expectedValue)}, '
              'Actual: ${Formatters.compact(alert.actualValue)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Deviation: ${alert.deviationPct.toStringAsFixed(1)}%',
                  style: TextStyle(
                    fontSize: 12,
                    color: severityColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (!alert.acknowledged)
                  TextButton(
                    onPressed: onAcknowledge,
                    child: const Text('Acknowledge'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return AppColors.error;
      case 'high':
        return const Color(0xFFDC2626);
      case 'medium':
        return AppColors.warning;
      case 'low':
        return AppColors.info;
      default:
        return Colors.grey;
    }
  }
}
