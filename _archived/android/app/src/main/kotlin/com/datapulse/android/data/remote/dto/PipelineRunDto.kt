package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PipelineRunDto(
    val id: String = "",
    @SerialName("tenant_id") val tenantId: Int = 0,
    @SerialName("run_type") val runType: String = "",
    val status: String = "",
    @SerialName("trigger_source") val triggerSource: String? = null,
    @SerialName("started_at") val startedAt: String = "",
    @SerialName("finished_at") val finishedAt: String? = null,
    @SerialName("duration_seconds") val durationSeconds: Double? = null,
    @SerialName("rows_loaded") val rowsLoaded: Int? = null,
    @SerialName("error_message") val errorMessage: String? = null,
    val metadata: Map<String, String> = emptyMap(),
)
