import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../core/network/api_client.dart';

class SqlLabScreen extends ConsumerStatefulWidget {
  const SqlLabScreen({super.key});

  @override
  ConsumerState<SqlLabScreen> createState() => _SqlLabScreenState();
}

class _SqlLabScreenState extends ConsumerState<SqlLabScreen> {
  final _controller = TextEditingController(
    text: 'SELECT\n  product_key,\n  drug_name,\n  SUM(net_amount) as revenue\n'
        'FROM public_marts.fct_sales f\n'
        'JOIN public_marts.dim_product p USING (product_key)\n'
        'GROUP BY 1, 2\nORDER BY revenue DESC\nLIMIT 10',
  );
  bool _loading = false;
  String? _queryId;
  List<String>? _columns;
  List<Map<String, dynamic>>? _rows;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                'SQL Lab',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const Spacer(),
              FilledButton.icon(
                onPressed: _loading ? null : _executeQuery,
                icon: _loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.play_arrow_rounded, size: 18),
                label: Text(_loading ? 'Running...' : 'Execute'),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // SQL editor
          Card(
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: TextField(
                controller: _controller,
                maxLines: 10,
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 13,
                ),
                decoration: const InputDecoration(
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.all(12),
                  hintText: 'Enter SQL query (SELECT only)...',
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Error
          if (_error != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.error.withOpacity(0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                _error!,
                style: const TextStyle(
                  color: AppColors.error,
                  fontSize: 13,
                  fontFamily: 'monospace',
                ),
              ),
            ),

          // Results
          if (_columns != null && _rows != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '${_rows!.length} rows returned',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Colors.grey,
                          ),
                    ),
                    const SizedBox(height: 8),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: DataTable(
                        columns: _columns!
                            .map((c) => DataColumn(
                                  label: Text(
                                    c,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w600,
                                      fontSize: 12,
                                    ),
                                  ),
                                ))
                            .toList(),
                        rows: _rows!
                            .take(100)
                            .map((row) => DataRow(
                                  cells: _columns!
                                      .map((c) => DataCell(
                                            Text(
                                              '${row[c] ?? ''}',
                                              style: const TextStyle(
                                                fontSize: 12,
                                                fontFamily: 'monospace',
                                              ),
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
      ),
    );
  }

  Future<void> _executeQuery() async {
    final sql = _controller.text.trim();
    if (sql.isEmpty) return;

    setState(() {
      _loading = true;
      _error = null;
      _columns = null;
      _rows = null;
    });

    try {
      final api = ref.read(apiClientProvider);

      // Submit query
      final submitResult = await api.post<Map<String, dynamic>>(
        '/queries',
        data: {'sql': sql},
      );
      final queryId = submitResult['query_id'] as String;

      // Poll for results
      Map<String, dynamic> result;
      while (true) {
        await Future.delayed(const Duration(milliseconds: 500));
        result = await api.get<Map<String, dynamic>>('/queries/$queryId');
        final status = result['status'] as String?;
        if (status == 'completed' || status == 'failed') break;
      }

      if (result['status'] == 'failed') {
        setState(() => _error = result['error'] as String? ?? 'Query failed');
      } else {
        setState(() {
          _columns = List<String>.from(result['columns'] ?? []);
          _rows = (result['rows'] as List?)
                  ?.map((r) => Map<String, dynamic>.from(r))
                  .toList() ??
              [];
        });
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }
}
