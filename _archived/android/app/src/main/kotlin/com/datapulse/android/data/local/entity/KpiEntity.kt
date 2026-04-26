package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "kpi_cache")
data class KpiEntity(
    @PrimaryKey val id: Int = 1,
    val todayNet: Double,
    val mtdNet: Double,
    val ytdNet: Double,
    val momGrowthPct: Double?,
    val yoyGrowthPct: Double?,
    val dailyTransactions: Int,
    val dailyCustomers: Int,
    val cachedAt: Long,
)
