import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../core/utils/formatters.dart';

class DateRangePickerButton extends StatelessWidget {
  final DateTime? startDate;
  final DateTime? endDate;
  final ValueChanged<DateTimeRange> onChanged;

  const DateRangePickerButton({
    super.key,
    this.startDate,
    this.endDate,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      icon: const Icon(Icons.calendar_today_rounded, size: 16),
      label: Text(
        startDate != null && endDate != null
            ? '${Formatters.shortDate(startDate)} - ${Formatters.shortDate(endDate)}'
            : 'Select dates',
        style: const TextStyle(fontSize: 13),
      ),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      onPressed: () async {
        final range = await showDateRangePicker(
          context: context,
          firstDate: DateTime(2023),
          lastDate: DateTime.now(),
          initialDateRange: startDate != null && endDate != null
              ? DateTimeRange(start: startDate!, end: endDate!)
              : null,
          builder: (context, child) {
            return Theme(
              data: Theme.of(context).copyWith(
                colorScheme: Theme.of(context).colorScheme.copyWith(
                      primary: AppColors.primary,
                    ),
              ),
              child: child!,
            );
          },
        );
        if (range != null) {
          onChanged(range);
        }
      },
    );
  }
}

class DatePresets extends StatelessWidget {
  final String? selected;
  final ValueChanged<String> onSelected;

  const DatePresets({
    super.key,
    this.selected,
    required this.onSelected,
  });

  static const _presets = {
    'today': 'Today',
    'yesterday': 'Yesterday',
    'last_7d': 'Last 7d',
    'last_30d': 'Last 30d',
    'this_month': 'This Month',
    'last_month': 'Last Month',
    'this_year': 'YTD',
  };

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: _presets.entries.map((entry) {
          final isSelected = selected == entry.key;
          return Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ChoiceChip(
              label: Text(entry.value, style: const TextStyle(fontSize: 12)),
              selected: isSelected,
              onSelected: (_) => onSelected(entry.key),
              selectedColor: AppColors.primary.withOpacity(0.15),
              labelStyle: TextStyle(
                color: isSelected ? AppColors.primary : null,
                fontWeight: isSelected ? FontWeight.w600 : null,
              ),
              visualDensity: const VisualDensity(vertical: -2),
            ),
          );
        }).toList(),
      ),
    );
  }
}
