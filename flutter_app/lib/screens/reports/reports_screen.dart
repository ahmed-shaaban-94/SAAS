import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../models/report.dart';
import '../../services/reports_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';
import '../../widgets/empty_state.dart';

final reportTemplatesProvider =
    FutureProvider.autoDispose<List<ReportTemplate>>((ref) async {
  final service = ref.watch(reportsServiceProvider);
  return service.getTemplates();
});

class ReportsScreen extends ConsumerWidget {
  const ReportsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final templates = ref.watch(reportTemplatesProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(reportTemplatesProvider),
      child: templates.when(
        loading: () => const Padding(
          padding: EdgeInsets.all(16),
          child: LoadingShimmer(itemCount: 4, height: 100),
        ),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(reportTemplatesProvider),
        ),
        data: (items) => items.isEmpty
            ? const EmptyState(
                icon: Icons.description_outlined,
                title: 'No Report Templates',
                subtitle: 'Report templates will appear here',
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final template = items[index];
                  return Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      contentPadding: const EdgeInsets.all(16),
                      leading: Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(
                          Icons.description_rounded,
                          color: AppColors.primary,
                        ),
                      ),
                      title: Text(
                        template.name,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          template.description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: () {
                        // Navigate to report render / parameters
                        _showRenderDialog(context, ref, template);
                      },
                    ),
                  );
                },
              ),
      ),
    );
  }

  void _showRenderDialog(
    BuildContext context,
    WidgetRef ref,
    ReportTemplate template,
  ) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.5,
        minChildSize: 0.3,
        maxChildSize: 0.9,
        expand: false,
        builder: (context, scrollController) => Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.withOpacity(0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                template.name,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 8),
              Text(template.description),
              const SizedBox(height: 20),
              Text(
                'Type: ${template.type}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                'Parameters: ${template.parameters.length}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const Spacer(),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () async {
                    Navigator.pop(context);
                    final service = ref.read(reportsServiceProvider);
                    try {
                      await service.renderReport(template.id, {});
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                              content: Text('Report generated!')),
                        );
                      }
                    } catch (e) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text('Error: $e')),
                        );
                      }
                    }
                  },
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Generate Report'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
