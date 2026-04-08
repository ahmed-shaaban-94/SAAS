class Target {
  final String id;
  final String metric; // revenue, transactions, customers
  final String period; // daily, monthly, quarterly, yearly
  final double targetValue;
  final double? actualValue;
  final double? achievementPct;
  final String? staffKey;
  final String? siteKey;
  final DateTime startDate;
  final DateTime endDate;

  const Target({
    required this.id,
    required this.metric,
    required this.period,
    required this.targetValue,
    this.actualValue,
    this.achievementPct,
    this.staffKey,
    this.siteKey,
    required this.startDate,
    required this.endDate,
  });

  bool get isAchieved => (achievementPct ?? 0) >= 100;

  factory Target.fromJson(Map<String, dynamic> json) => Target(
        id: json['id'] as String,
        metric: json['metric'] as String,
        period: json['period'] as String,
        targetValue: (json['target_value'] as num).toDouble(),
        actualValue: (json['actual_value'] as num?)?.toDouble(),
        achievementPct: (json['achievement_pct'] as num?)?.toDouble(),
        staffKey: json['staff_key'] as String?,
        siteKey: json['site_key'] as String?,
        startDate: DateTime.parse(json['start_date'] as String),
        endDate: DateTime.parse(json['end_date'] as String),
      );
}

class TargetSummary {
  final int totalTargets;
  final int achievedTargets;
  final double overallAchievement;
  final List<Target> targets;

  const TargetSummary({
    required this.totalTargets,
    required this.achievedTargets,
    required this.overallAchievement,
    required this.targets,
  });

  factory TargetSummary.fromJson(Map<String, dynamic> json) => TargetSummary(
        totalTargets: json['total_targets'] as int,
        achievedTargets: json['achieved_targets'] as int,
        overallAchievement:
            (json['overall_achievement'] as num).toDouble(),
        targets: (json['targets'] as List)
            .map((e) => Target.fromJson(e))
            .toList(),
      );
}
