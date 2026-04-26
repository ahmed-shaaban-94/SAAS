package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class KpiSummaryDto(
    @SerialName("today_net") val todayNet: Double = 0.0,
    @SerialName("mtd_net") val mtdNet: Double = 0.0,
    @SerialName("ytd_net") val ytdNet: Double = 0.0,
    @SerialName("mom_growth_pct") val momGrowthPct: Double? = null,
    @SerialName("yoy_growth_pct") val yoyGrowthPct: Double? = null,
    @SerialName("daily_transactions") val dailyTransactions: Int = 0,
    @SerialName("daily_customers") val dailyCustomers: Int = 0,
)
