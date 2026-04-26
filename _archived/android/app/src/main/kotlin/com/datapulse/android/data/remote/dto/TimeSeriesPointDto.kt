package com.datapulse.android.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class TimeSeriesPointDto(
    val period: String,
    val value: Double = 0.0,
)
