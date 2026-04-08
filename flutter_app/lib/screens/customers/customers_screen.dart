import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/utils/formatters.dart';
import '../../providers/analytics_provider.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

class CustomersScreen extends ConsumerWidget {
  const CustomersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final customers = ref.watch(topCustomersProvider);

    return customers.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 8, height: 72),
      ),
      error: (error, _) => ErrorView(
        message: error.toString(),
        onRetry: () => ref.invalidate(topCustomersProvider),
      ),
      data: (data) => RefreshIndicator(
        onRefresh: () async => ref.invalidate(topCustomersProvider),
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: data.items.length,
          itemBuilder: (context, index) {
            final item = data.items[index];
            return Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor:
                      Theme.of(context).colorScheme.secondaryContainer,
                  child: Text(
                    item.name.isNotEmpty ? item.name[0].toUpperCase() : '?',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: Theme.of(context)
                          .colorScheme
                          .onSecondaryContainer,
                    ),
                  ),
                ),
                title: Text(
                  item.name,
                  style: const TextStyle(fontWeight: FontWeight.w500),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text(
                  '${item.pctOfTotal.toStringAsFixed(1)}% of total',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                trailing: Text(
                  Formatters.compact(item.value),
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                onTap: () => context.go('/customers/${item.key}'),
              ),
            );
          },
        ),
      ),
    );
  }
}
