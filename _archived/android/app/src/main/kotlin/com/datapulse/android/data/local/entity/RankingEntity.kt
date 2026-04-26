package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "ranking_cache")
data class RankingEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val category: String,
    val rank: Int,
    val itemKey: Int,
    val name: String,
    val value: Double,
    val pctOfTotal: Double,
    val total: Double,
    val cachedAt: Long,
)
