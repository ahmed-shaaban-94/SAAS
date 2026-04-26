package com.datapulse.android.data.mapper

import com.datapulse.android.data.local.entity.*
import com.datapulse.android.data.remote.dto.*
import com.datapulse.android.domain.model.*

object AnalyticsMapper {

    fun KpiSummaryDto.toDomain() = KpiSummary(
        todayNet = todayNet,
        mtdNet = mtdNet,
        ytdNet = ytdNet,
        momGrowthPct = momGrowthPct,
        yoyGrowthPct = yoyGrowthPct,
        dailyTransactions = dailyTransactions,
        dailyCustomers = dailyCustomers,
    )

    fun KpiSummary.toEntity(cachedAt: Long = System.currentTimeMillis()) = KpiEntity(
        todayNet = todayNet,
        mtdNet = mtdNet,
        ytdNet = ytdNet,
        momGrowthPct = momGrowthPct,
        yoyGrowthPct = yoyGrowthPct,
        dailyTransactions = dailyTransactions,
        dailyCustomers = dailyCustomers,
        cachedAt = cachedAt,
    )

    fun KpiEntity.toDomain() = KpiSummary(
        todayNet = todayNet,
        mtdNet = mtdNet,
        ytdNet = ytdNet,
        momGrowthPct = momGrowthPct,
        yoyGrowthPct = yoyGrowthPct,
        dailyTransactions = dailyTransactions,
        dailyCustomers = dailyCustomers,
    )

    fun TimeSeriesPointDto.toDomain() = TimeSeriesPoint(period = period, value = value)

    fun TrendResultDto.toDomain() = TrendResult(
        points = points.map { it.toDomain() },
        total = total,
        average = average,
        minimum = minimum,
        maximum = maximum,
        growthPct = growthPct,
    )

    fun RankingItemDto.toDomain() = RankingItem(
        rank = rank, key = key, name = name, value = value, pctOfTotal = pctOfTotal,
    )

    fun RankingResultDto.toDomain() = RankingResult(
        items = items.map { it.toDomain() },
        total = total,
    )

    fun RankingResult.toEntities(category: String, cachedAt: Long = System.currentTimeMillis()) =
        items.map { item ->
            RankingEntity(
                category = category,
                rank = item.rank,
                itemKey = item.key,
                name = item.name,
                value = item.value,
                pctOfTotal = item.pctOfTotal,
                total = total,
                cachedAt = cachedAt,
            )
        }

    fun List<RankingEntity>.toRankingResult(): RankingResult? {
        if (isEmpty()) return null
        return RankingResult(
            items = map { RankingItem(it.rank, it.itemKey, it.name, it.value, it.pctOfTotal) },
            total = first().total,
        )
    }

    fun ReturnAnalysisDto.toDomain() = ReturnAnalysis(
        drugName = drugName,
        customerName = customerName,
        returnQuantity = returnQuantity,
        returnAmount = returnAmount,
        returnCount = returnCount,
    )

    fun ReturnAnalysis.toEntity(cachedAt: Long = System.currentTimeMillis()) = ReturnEntity(
        drugName = drugName,
        customerName = customerName,
        returnQuantity = returnQuantity,
        returnAmount = returnAmount,
        returnCount = returnCount,
        cachedAt = cachedAt,
    )

    fun ReturnEntity.toDomain() = ReturnAnalysis(
        drugName = drugName,
        customerName = customerName,
        returnQuantity = returnQuantity,
        returnAmount = returnAmount,
        returnCount = returnCount,
    )

    fun HealthStatusDto.toDomain() = HealthStatus(status = status, db = db)

    fun List<TimeSeriesPoint>.toDailyEntities(cachedAt: Long = System.currentTimeMillis()) =
        map { DailyTrendEntity(period = it.period, value = it.value, cachedAt = cachedAt) }

    fun List<TimeSeriesPoint>.toMonthlyEntities(cachedAt: Long = System.currentTimeMillis()) =
        map { MonthlyTrendEntity(period = it.period, value = it.value, cachedAt = cachedAt) }

    fun List<DailyTrendEntity>.toDailyPoints() =
        map { TimeSeriesPoint(period = it.period, value = it.value) }

    fun List<MonthlyTrendEntity>.toMonthlyPoints() =
        map { TimeSeriesPoint(period = it.period, value = it.value) }
}
