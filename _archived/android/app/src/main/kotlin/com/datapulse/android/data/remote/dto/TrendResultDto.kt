package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class TrendResultDto(
    val points: List<TimeSeriesPointDto> = emptyList(),
    val total: Double = 0.0,
    val average: Double = 0.0,
    val minimum: Double = 0.0,
    val maximum: Double = 0.0,
    @SerialName("growth_pct") val growthPct: Double? = null,
)
