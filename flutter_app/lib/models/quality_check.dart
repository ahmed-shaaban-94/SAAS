class QualityCheck {
  final String id;
  final String runId;
  final String checkName;
  final String stage;
  final String status; // passed, failed, warning
  final String? message;
  final double? score;
  final DateTime checkedAt;

  const QualityCheck({
    required this.id,
    required this.runId,
    required this.checkName,
    required this.stage,
    required this.status,
    this.message,
    this.score,
    required this.checkedAt,
  });

  bool get isPassed => status == 'passed';
  bool get isFailed => status == 'failed';
  bool get isWarning => status == 'warning';

  factory QualityCheck.fromJson(Map<String, dynamic> json) => QualityCheck(
        id: json['id'] as String,
        runId: json['run_id'] as String,
        checkName: json['check_name'] as String,
        stage: json['stage'] as String,
        status: json['status'] as String,
        message: json['message'] as String?,
        score: (json['score'] as num?)?.toDouble(),
        checkedAt: DateTime.parse(json['checked_at'] as String),
      );
}

class QualityScorecard {
  final double overallScore;
  final int totalChecks;
  final int passedChecks;
  final int failedChecks;
  final int warningChecks;
  final Map<String, double> stageScores;

  const QualityScorecard({
    required this.overallScore,
    required this.totalChecks,
    required this.passedChecks,
    required this.failedChecks,
    required this.warningChecks,
    required this.stageScores,
  });

  factory QualityScorecard.fromJson(Map<String, dynamic> json) =>
      QualityScorecard(
        overallScore: (json['overall_score'] as num).toDouble(),
        totalChecks: json['total_checks'] as int,
        passedChecks: json['passed_checks'] as int,
        failedChecks: json['failed_checks'] as int,
        warningChecks: json['warning_checks'] as int,
        stageScores: (json['stage_scores'] as Map<String, dynamic>)
            .map((k, v) => MapEntry(k, (v as num).toDouble())),
      );
}
