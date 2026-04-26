package com.datapulse.android.domain.model

data class RankingItem(
    val rank: Int,
    val key: Int,
    val name: String,
    val value: Double,
    val pctOfTotal: Double,
)
