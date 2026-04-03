package com.datapulse.android.domain.model

data class AISummary(
    val summary: String,
    val generatedAt: String?,
)

data class AnomalyItem(
    val metric: String,
    val date: String,
    val value: Double,
    val zScore: Double,
    val direction: String,
    val severity: String,
)

data class AnomalyReport(
    val anomalies: List<AnomalyItem>,
    val checkedAt: String?,
)
