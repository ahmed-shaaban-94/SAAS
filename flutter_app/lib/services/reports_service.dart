import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/report.dart';

final reportsServiceProvider = Provider<ReportsService>((ref) {
  return ReportsService(ref.watch(apiClientProvider));
});

class ReportsService {
  final ApiClient _api;

  ReportsService(this._api);

  Future<List<ReportTemplate>> getTemplates() async {
    return _api.get(
      '/reports',
      fromJson: (data) => (data as List)
          .map((e) => ReportTemplate.fromJson(e))
          .toList(),
    );
  }

  Future<ReportTemplate> getTemplate(String templateId) async {
    return _api.get(
      '/reports/$templateId',
      fromJson: (data) => ReportTemplate.fromJson(data),
    );
  }

  Future<RenderedReport> renderReport(
    String templateId,
    Map<String, dynamic> parameters,
  ) async {
    return _api.post(
      '/reports/$templateId/render',
      data: parameters,
      fromJson: (data) => RenderedReport.fromJson(data),
    );
  }
}
