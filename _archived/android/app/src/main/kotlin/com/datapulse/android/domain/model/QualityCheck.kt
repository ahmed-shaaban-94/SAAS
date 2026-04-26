package com.datapulse.android.domain.model

data class QualityCheck(
    val id: Int,
    val pipelineRunId: String,
    val checkName: String,
    val stage: String,
    val passed: Boolean,
    val severity: String,
    val message: String,
    val details: Map<String, String>,
    val createdAt: String,
)
