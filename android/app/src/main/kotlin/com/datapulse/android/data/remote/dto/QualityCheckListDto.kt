package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class QualityCheckListDto(
    @SerialName("run_id") val runId: String = "",
    val checks: List<QualityCheckDto> = emptyList(),
    @SerialName("total_checks") val totalChecks: Int = 0,
    val passed: Int = 0,
    val failed: Int = 0,
    val warned: Int = 0,
)
