package com.datapulse.android.domain.model

data class PipelineRun(
    val id: String,
    val tenantId: Int,
    val runType: String,
    val status: String,
    val triggerSource: String?,
    val startedAt: String,
    val finishedAt: String?,
    val durationSeconds: Double?,
    val rowsLoaded: Int?,
    val errorMessage: String?,
    val metadata: Map<String, String>,
)
