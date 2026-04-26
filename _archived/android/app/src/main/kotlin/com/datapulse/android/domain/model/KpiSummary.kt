package com.datapulse.android.domain.model

data class KpiSummary(
    val todayNet: Double,
    val mtdNet: Double,
    val ytdNet: Double,
    val momGrowthPct: Double?,
    val yoyGrowthPct: Double?,
    val dailyTransactions: Int,
    val dailyCustomers: Int,
)
