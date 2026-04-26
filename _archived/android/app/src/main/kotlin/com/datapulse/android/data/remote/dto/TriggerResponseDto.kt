package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class TriggerResponseDto(
    @SerialName("run_id") val runId: String = "",
    val status: String = "",
    val message: String = "",
)
