package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class RankingItemDto(
    val rank: Int = 0,
    val key: Int = 0,
    val name: String = "",
    val value: Double = 0.0,
    @SerialName("pct_of_total") val pctOfTotal: Double = 0.0,
)
