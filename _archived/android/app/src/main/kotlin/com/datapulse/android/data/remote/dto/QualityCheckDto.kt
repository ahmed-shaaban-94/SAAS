package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class QualityCheckDto(
    val id: Int = 0,
    @SerialName("pipeline_run_id") val pipelineRunId: String = "",
    @SerialName("check_name") val checkName: String = "",
    val stage: String = "",
    val passed: Boolean = true,
    val severity: String = "info",
    val message: String = "",
    val details: Map<String, String> = emptyMap(),
    @SerialName("created_at") val createdAt: String = "",
)
