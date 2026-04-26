package com.datapulse.android.domain.model

data class AlertLogItem(
    val id: Int,
    val alertType: String,
    val message: String,
    val severity: String,
    val createdAt: String,
    val acknowledgedAt: String?,
)
