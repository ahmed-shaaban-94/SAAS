import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/pipeline_run.dart';
import '../models/quality_check.dart';

final pipelineServiceProvider = Provider<PipelineService>((ref) {
  return PipelineService(ref.watch(apiClientProvider));
});

class PipelineService {
  final ApiClient _api;

  PipelineService(this._api);

  Future<PipelineRunList> getRuns({
    String? status,
    int offset = 0,
    int limit = 20,
  }) async {
    return _api.get(
      '/pipeline/runs',
      queryParameters: {
        if (status != null) 'status': status,
        'offset': offset,
        'limit': limit,
      },
      fromJson: (data) => PipelineRunList.fromJson(data),
    );
  }

  Future<PipelineRun> getLatestRun() async {
    return _api.get(
      '/pipeline/runs/latest',
      fromJson: (data) => PipelineRun.fromJson(data),
    );
  }

  Future<PipelineRun> getRun(String runId) async {
    return _api.get(
      '/pipeline/runs/$runId',
      fromJson: (data) => PipelineRun.fromJson(data),
    );
  }

  Future<TriggerResponse> triggerPipeline() async {
    return _api.post(
      '/pipeline/trigger',
      fromJson: (data) => TriggerResponse.fromJson(data),
    );
  }

  Future<List<QualityCheck>> getQualityChecks(String runId, {String? stage}) async {
    return _api.get(
      '/pipeline/runs/$runId/quality',
      queryParameters: {
        if (stage != null) 'stage': stage,
      },
      fromJson: (data) => (data['items'] as List)
          .map((e) => QualityCheck.fromJson(e))
          .toList(),
    );
  }

  Future<QualityScorecard> getQualityScorecard() async {
    return _api.get(
      '/pipeline/quality/scorecard',
      fromJson: (data) => QualityScorecard.fromJson(data),
    );
  }
}
