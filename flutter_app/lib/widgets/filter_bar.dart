import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/filter_options.dart';
import '../providers/dashboard_provider.dart';
import 'date_range_picker.dart';

class FilterBar extends ConsumerWidget {
  final FilterOptions? options;

  const FilterBar({super.key, this.options});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(filterProvider);

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          DateRangePickerButton(
            startDate: filter.startDate,
            endDate: filter.endDate,
            onChanged: (range) {
              ref.read(filterProvider.notifier).state = filter.copyWith(
                startDate: range.start,
                endDate: range.end,
              );
            },
          ),
          const SizedBox(width: 8),
          if (options != null && options!.sites.isNotEmpty)
            _FilterDropdown(
              label: 'Site',
              value: filter.siteKey,
              items: options!.sites
                  .map((s) => DropdownMenuItem(
                        value: s.key,
                        child: Text(s.label, style: const TextStyle(fontSize: 13)),
                      ))
                  .toList(),
              onChanged: (val) {
                ref.read(filterProvider.notifier).state =
                    filter.copyWith(siteKey: val);
              },
            ),
          const SizedBox(width: 8),
          if (options != null && options!.categories.isNotEmpty)
            _FilterDropdown(
              label: 'Category',
              value: filter.category,
              items: options!.categories
                  .map((c) => DropdownMenuItem(
                        value: c,
                        child: Text(c, style: const TextStyle(fontSize: 13)),
                      ))
                  .toList(),
              onChanged: (val) {
                ref.read(filterProvider.notifier).state =
                    filter.copyWith(category: val);
              },
            ),
          const SizedBox(width: 8),
          if (filter.startDate != null ||
              filter.siteKey != null ||
              filter.category != null)
            TextButton.icon(
              icon: const Icon(Icons.clear_rounded, size: 16),
              label: const Text('Clear', style: TextStyle(fontSize: 12)),
              onPressed: () {
                ref.read(filterProvider.notifier).state =
                    const AnalyticsFilter();
              },
            ),
        ],
      ),
    );
  }
}

class _FilterDropdown extends StatelessWidget {
  final String label;
  final String? value;
  final List<DropdownMenuItem<String>> items;
  final ValueChanged<String?> onChanged;

  const _FilterDropdown({
    required this.label,
    this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).dividerColor),
        borderRadius: BorderRadius.circular(8),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: value,
          hint: Text(label, style: const TextStyle(fontSize: 13)),
          isDense: true,
          items: [
            DropdownMenuItem(
              value: null,
              child: Text('All $label', style: const TextStyle(fontSize: 13)),
            ),
            ...items,
          ],
          onChanged: onChanged,
        ),
      ),
    );
  }
}
