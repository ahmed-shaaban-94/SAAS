import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/target.dart';

final targetsServiceProvider = Provider<TargetsService>((ref) {
  return TargetsService(ref.watch(apiClientProvider));
});

class TargetsService {
  final ApiClient _api;

  TargetsService(this._api);

  Future<List<Target>> getTargets({
    String? metric,
    String? period,
  }) async {
    return _api.get(
      '/targets',
      queryParameters: {
        if (metric != null) 'metric': metric,
        if (period != null) 'period': period,
      },
      fromJson: (data) =>
          (data as List).map((e) => Target.fromJson(e)).toList(),
    );
  }

  Future<Target> createTarget(Map<String, dynamic> data) async {
    return _api.post(
      '/targets',
      data: data,
      fromJson: (d) => Target.fromJson(d),
    );
  }

  Future<void> deleteTarget(String targetId) async {
    await _api.delete('/targets/$targetId');
  }

  Future<TargetSummary> getSummary() async {
    return _api.get(
      '/targets/summary',
      fromJson: (data) => TargetSummary.fromJson(data),
    );
  }
}
