import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/anomaly_alert.dart';

final anomalyServiceProvider = Provider<AnomalyService>((ref) {
  return AnomalyService(ref.watch(apiClientProvider));
});

class AnomalyService {
  final ApiClient _api;

  AnomalyService(this._api);

  Future<List<AnomalyAlert>> getActiveAlerts() async {
    return _api.get(
      '/anomalies/active',
      fromJson: (data) =>
          (data as List).map((e) => AnomalyAlert.fromJson(e)).toList(),
    );
  }

  Future<List<AnomalyAlert>> getAlertHistory({
    String? startDate,
    String? endDate,
  }) async {
    return _api.get(
      '/anomalies/history',
      queryParameters: {
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
      },
      fromJson: (data) =>
          (data as List).map((e) => AnomalyAlert.fromJson(e)).toList(),
    );
  }

  Future<void> acknowledgeAlert(String alertId) async {
    await _api.post('/anomalies/$alertId/acknowledge');
  }
}
