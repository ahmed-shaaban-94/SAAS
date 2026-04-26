package com.datapulse.android.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class RankingResultDto(
    val items: List<RankingItemDto> = emptyList(),
    val total: Double = 0.0,
)
