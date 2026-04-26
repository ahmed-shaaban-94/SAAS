package com.datapulse.android.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class HealthStatusDto(
    val status: String,
    val db: String? = null,
)
