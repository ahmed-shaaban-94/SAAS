package com.datapulse.android.domain.model

data class TrendResult(
    val points: List<TimeSeriesPoint>,
    val total: Double,
    val average: Double,
    val minimum: Double,
    val maximum: Double,
    val growthPct: Double?,
)
