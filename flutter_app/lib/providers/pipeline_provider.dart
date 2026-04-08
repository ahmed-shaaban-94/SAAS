import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/pipeline_run.dart';
import '../models/quality_check.dart';
import '../services/pipeline_service.dart';

final pipelineRunsProvider =
    FutureProvider.autoDispose<PipelineRunList>((ref) async {
  final service = ref.watch(pipelineServiceProvider);
  return service.getRuns();
});

final latestRunProvider =
    FutureProvider.autoDispose<PipelineRun>((ref) async {
  final service = ref.watch(pipelineServiceProvider);
  return service.getLatestRun();
});

final qualityScorecardProvider =
    FutureProvider.autoDispose<QualityScorecard>((ref) async {
  final service = ref.watch(pipelineServiceProvider);
  return service.getQualityScorecard();
});
