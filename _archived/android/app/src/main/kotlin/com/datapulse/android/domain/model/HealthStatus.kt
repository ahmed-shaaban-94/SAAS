package com.datapulse.android.domain.model

data class HealthStatus(
    val status: String,
    val db: String?,
) {
    val isHealthy: Boolean get() = status == "ok"
    val isDegraded: Boolean get() = status == "ok" && db != "ok"
}
