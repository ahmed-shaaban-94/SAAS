class PipelineRun {
  final String id;
  final String status; // pending, running, success, failed, cancelled
  final String? stage;
  final DateTime startedAt;
  final DateTime? completedAt;
  final int? rowsProcessed;
  final int? rowsFailed;
  final double? durationSeconds;
  final String? errorMessage;

  const PipelineRun({
    required this.id,
    required this.status,
    this.stage,
    required this.startedAt,
    this.completedAt,
    this.rowsProcessed,
    this.rowsFailed,
    this.durationSeconds,
    this.errorMessage,
  });

  bool get isRunning => status == 'running' || status == 'pending';
  bool get isSuccess => status == 'success';
  bool get isFailed => status == 'failed';

  factory PipelineRun.fromJson(Map<String, dynamic> json) => PipelineRun(
        id: json['id'] as String,
        status: json['status'] as String,
        stage: json['stage'] as String?,
        startedAt: DateTime.parse(json['started_at'] as String),
        completedAt: json['completed_at'] != null
            ? DateTime.parse(json['completed_at'] as String)
            : null,
        rowsProcessed: json['rows_processed'] as int?,
        rowsFailed: json['rows_failed'] as int?,
        durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
        errorMessage: json['error_message'] as String?,
      );
}

class PipelineRunList {
  final List<PipelineRun> items;
  final int total;

  const PipelineRunList({required this.items, required this.total});

  factory PipelineRunList.fromJson(Map<String, dynamic> json) =>
      PipelineRunList(
        items: (json['items'] as List)
            .map((e) => PipelineRun.fromJson(e))
            .toList(),
        total: json['total'] as int,
      );
}

class TriggerResponse {
  final String runId;
  final String status;
  final String message;

  const TriggerResponse({
    required this.runId,
    required this.status,
    required this.message,
  });

  factory TriggerResponse.fromJson(Map<String, dynamic> json) =>
      TriggerResponse(
        runId: json['run_id'] as String,
        status: json['status'] as String,
        message: json['message'] as String,
      );
}
