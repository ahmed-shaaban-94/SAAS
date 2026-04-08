import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/utils/formatters.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class SitesScreen extends ConsumerWidget {
  const SitesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sites = ref.watch(sitesProvider);

    return sites.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 4, height: 100),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(sitesProvider),
      ),
      data: (data) => RefreshIndicator(
        onRefresh: () async => ref.invalidate(sitesProvider),
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: data.items.length,
          itemBuilder: (context, index) {
            final item = data.items[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                leading: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Theme.of(context)
                        .colorScheme
                        .primaryContainer
                        .withOpacity(0.5),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.store_rounded),
                ),
                title: Text(
                  item.name,
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                subtitle: Text(
                  '${item.pctOfTotal.toStringAsFixed(1)}% of total revenue',
                ),
                trailing: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      Formatters.compact(item.value),
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    Text(
                      'Revenue',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
                onTap: () => context.go('/sites/${item.key}'),
              ),
            );
          },
        ),
      ),
    );
  }
}
