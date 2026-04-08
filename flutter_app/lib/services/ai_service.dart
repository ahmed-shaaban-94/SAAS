import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/ai_summary.dart';

final aiServiceProvider = Provider<AiService>((ref) {
  return AiService(ref.watch(apiClientProvider));
});

class AiService {
  final ApiClient _api;

  AiService(this._api);

  Future<bool> checkAvailability() async {
    final result = await _api.get<Map<String, dynamic>>('/ai-light/status');
    return result['available'] as bool? ?? false;
  }

  Future<AiSummary> getSummary({Map<String, dynamic>? params}) async {
    return _api.get(
      '/ai-light/summary',
      queryParameters: params,
      fromJson: (data) => AiSummary.fromJson(data),
    );
  }

  Future<AnomalyReport> getAnomalies({Map<String, dynamic>? params}) async {
    return _api.get(
      '/ai-light/anomalies',
      queryParameters: params,
      fromJson: (data) => AnomalyReport.fromJson(data),
    );
  }

  Future<ChangeNarrative> getChanges({Map<String, dynamic>? params}) async {
    return _api.get(
      '/ai-light/changes',
      queryParameters: params,
      fromJson: (data) => ChangeNarrative.fromJson(data),
    );
  }
}
