package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "daily_trend_cache")
data class DailyTrendEntity(
    @PrimaryKey val period: String,
    val value: Double,
    val cachedAt: Long,
)
