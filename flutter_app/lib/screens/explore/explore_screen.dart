import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/utils/extensions.dart';
import '../../models/explore_model.dart';
import '../../services/explore_service.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/error_view.dart';

final exploreModelsProvider =
    FutureProvider.autoDispose<List<ExploreModel>>((ref) async {
  final service = ref.watch(exploreServiceProvider);
  return service.getModels();
});

class ExploreScreen extends ConsumerStatefulWidget {
  const ExploreScreen({super.key});

  @override
  ConsumerState<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends ConsumerState<ExploreScreen> {
  ExploreModel? _selectedModel;
  final _selectedDimensions = <String>{};
  final _selectedMetrics = <String>{};
  ExploreResult? _result;
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final models = ref.watch(exploreModelsProvider);

    return models.when(
      loading: () => const Padding(
        padding: EdgeInsets.all(16),
        child: LoadingShimmer(itemCount: 3),
      ),
      error: (e, _) => ErrorView(
        message: e.toString(),
        onRetry: () => ref.invalidate(exploreModelsProvider),
      ),
      data: (modelList) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Explore Data',
              style: context.textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 16),

            // Model selector
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Select Model',
                      style: context.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: _selectedModel?.name,
                      decoration: const InputDecoration(
                        hintText: 'Choose a data model',
                      ),
                      items: modelList
                          .map((m) => DropdownMenuItem(
                                value: m.name,
                                child: Text(m.name),
                              ))
                          .toList(),
                      onChanged: (val) {
                        setState(() {
                          _selectedModel =
                              modelList.firstWhere((m) => m.name == val);
                          _selectedDimensions.clear();
                          _selectedMetrics.clear();
                          _result = null;
                        });
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Dimensions & Metrics
            if (_selectedModel != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Dimensions',
                        style: context.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: _selectedModel!.dimensions
                            .map((d) => FilterChip(
                                  label: Text(d.name,
                                      style: const TextStyle(fontSize: 12)),
                                  selected:
                                      _selectedDimensions.contains(d.name),
                                  onSelected: (sel) {
                                    setState(() {
                                      if (sel) {
                                        _selectedDimensions.add(d.name);
                                      } else {
                                        _selectedDimensions.remove(d.name);
                                      }
                                    });
                                  },
                                ))
                            .toList(),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Metrics',
                        style: context.textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: _selectedModel!.metrics
                            .map((m) => FilterChip(
                                  label: Text(m.name,
                                      style: const TextStyle(fontSize: 12)),
                                  selected:
                                      _selectedMetrics.contains(m.name),
                                  selectedColor:
                                      AppColors.secondary.withOpacity(0.15),
                                  onSelected: (sel) {
                                    setState(() {
                                      if (sel) {
                                        _selectedMetrics.add(m.name);
                                      } else {
                                        _selectedMetrics.remove(m.name);
                                      }
                                    });
                                  },
                                ))
                            .toList(),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Run query
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: _selectedDimensions.isEmpty &&
                          _selectedMetrics.isEmpty
                      ? null
                      : _runQuery,
                  icon: _loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.play_arrow_rounded),
                  label: Text(_loading ? 'Running...' : 'Run Query'),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Results
            if (_result != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Results (${_result!.rowCount} rows)',
                            style: context.textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: DataTable(
                          columns: _result!.columns
                              .map((c) => DataColumn(
                                    label: Text(
                                      c,
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w600),
                                    ),
                                  ))
                              .toList(),
                          rows: _result!.rows
                              .take(50)
                              .map((row) => DataRow(
                                    cells: _result!.columns
                                        .map((c) => DataCell(
                                              Text(
                                                '${row[c] ?? ''}',
                                                style: const TextStyle(
                                                    fontSize: 13),
                                              ),
                                            ))
                                        .toList(),
                                  ))
                              .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _runQuery() async {
    if (_selectedModel == null) return;
    setState(() => _loading = true);
    try {
      final service = ref.read(exploreServiceProvider);
      final result = await service.executeQuery(
        model: _selectedModel!.name,
        dimensions: _selectedDimensions.toList(),
        metrics: _selectedMetrics.toList(),
      );
      setState(() => _result = result);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      setState(() => _loading = false);
    }
  }
}
