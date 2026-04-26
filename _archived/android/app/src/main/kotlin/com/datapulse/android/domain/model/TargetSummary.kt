package com.datapulse.android.domain.model

data class MonthTarget(
    val month: String,
    val target: Double,
    val actual: Double,
    val achievement: Double,
)

data class TargetSummary(
    val year: Int,
    val totalTarget: Double,
    val totalActual: Double,
    val overallAchievement: Double,
    val months: List<MonthTarget>,
)
