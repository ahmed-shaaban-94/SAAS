import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/health_status.dart';

final healthServiceProvider = Provider<HealthService>((ref) {
  return HealthService(ref.watch(apiClientProvider));
});

class HealthService {
  final ApiClient _api;

  HealthService(this._api);

  Future<HealthStatus> getHealth() async {
    return _api.get(
      '/health',
      fromJson: (data) => HealthStatus.fromJson(data),
    );
  }

  Future<HealthStatus> getReadiness() async {
    return _api.get(
      '/health/ready',
      fromJson: (data) => HealthStatus.fromJson(data),
    );
  }
}
