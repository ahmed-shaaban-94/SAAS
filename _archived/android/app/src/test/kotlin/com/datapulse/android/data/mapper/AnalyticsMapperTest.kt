package com.datapulse.android.data.mapper

import com.datapulse.android.data.local.entity.KpiEntity
import com.datapulse.android.data.local.entity.RankingEntity
import com.datapulse.android.data.local.entity.ReturnEntity
import com.datapulse.android.data.remote.dto.*
import com.datapulse.android.data.mapper.AnalyticsMapper.toDomain
import com.datapulse.android.data.mapper.AnalyticsMapper.toEntity
import com.datapulse.android.data.mapper.AnalyticsMapper.toEntities
import com.datapulse.android.data.mapper.AnalyticsMapper.toRankingResult
import com.datapulse.android.domain.model.KpiSummary
import com.datapulse.android.domain.model.RankingItem
import com.datapulse.android.domain.model.RankingResult
import com.datapulse.android.domain.model.ReturnAnalysis
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Test

class AnalyticsMapperTest {

    @Test
    fun `KpiSummaryDto toDomain maps all fields correctly`() {
        val dto = KpiSummaryDto(
            todayNet = 1000.0, mtdNet = 50000.0, ytdNet = 500000.0,
            momGrowthPct = 12.5, yoyGrowthPct = -3.2,
            dailyTransactions = 150, dailyCustomers = 42,
        )
        val domain = dto.toDomain()
        assertEquals(1000.0, domain.todayNet)
        assertEquals(50000.0, domain.mtdNet)
        assertEquals(500000.0, domain.ytdNet)
        assertEquals(12.5, domain.momGrowthPct)
        assertEquals(-3.2, domain.yoyGrowthPct)
        assertEquals(150, domain.dailyTransactions)
        assertEquals(42, domain.dailyCustomers)
    }

    @Test
    fun `KpiSummary toEntity and back preserves data`() {
        val original = KpiSummary(1000.0, 50000.0, 500000.0, 12.5, null, 150, 42)
        val entity = original.toEntity(cachedAt = 1000L)
        val restored = entity.toDomain()
        assertEquals(original, restored)
    }

    @Test
    fun `RankingResultDto toDomain maps items and total`() {
        val dto = RankingResultDto(
            items = listOf(
                RankingItemDto(rank = 1, key = 10, name = "Drug A", value = 5000.0, pctOfTotal = 50.0),
                RankingItemDto(rank = 2, key = 20, name = "Drug B", value = 3000.0, pctOfTotal = 30.0),
            ),
            total = 10000.0,
        )
        val domain = dto.toDomain()
        assertEquals(2, domain.items.size)
        assertEquals("Drug A", domain.items[0].name)
        assertEquals(10000.0, domain.total)
    }

    @Test
    fun `RankingResult toEntities creates entities with category`() {
        val result = RankingResult(
            items = listOf(RankingItem(1, 10, "Test", 5000.0, 100.0)),
            total = 5000.0,
        )
        val entities = result.toEntities("product", cachedAt = 1000L)
        assertEquals(1, entities.size)
        assertEquals("product", entities[0].category)
        assertEquals(1000L, entities[0].cachedAt)
    }

    @Test
    fun `empty entity list toRankingResult returns null`() {
        val result = emptyList<RankingEntity>().toRankingResult()
        assertNull(result)
    }

    @Test
    fun `ReturnAnalysisDto toDomain maps all fields`() {
        val dto = ReturnAnalysisDto("Drug X", "Customer Y", 10.0, 500.0, 3)
        val domain = dto.toDomain()
        assertEquals("Drug X", domain.drugName)
        assertEquals("Customer Y", domain.customerName)
        assertEquals(10.0, domain.returnQuantity)
        assertEquals(500.0, domain.returnAmount)
        assertEquals(3, domain.returnCount)
    }

    @Test
    fun `ReturnAnalysis roundtrip through entity`() {
        val original = ReturnAnalysis("Drug X", "Customer Y", 10.0, 500.0, 3)
        val entity = original.toEntity(cachedAt = 2000L)
        val restored = entity.toDomain()
        assertEquals(original, restored)
    }

    @Test
    fun `TrendResultDto toDomain maps points and stats`() {
        val dto = TrendResultDto(
            points = listOf(
                TimeSeriesPointDto("2024-01", 1000.0),
                TimeSeriesPointDto("2024-02", 2000.0),
            ),
            total = 3000.0, average = 1500.0, minimum = 1000.0, maximum = 2000.0,
            growthPct = 100.0,
        )
        val domain = dto.toDomain()
        assertEquals(2, domain.points.size)
        assertEquals("2024-01", domain.points[0].period)
        assertEquals(3000.0, domain.total)
        assertEquals(100.0, domain.growthPct)
    }

    @Test
    fun `HealthStatusDto toDomain maps status and db`() {
        val dto = HealthStatusDto(status = "ok", db = "ok")
        val domain = dto.toDomain()
        assertEquals(true, domain.isHealthy)
        assertEquals(false, domain.isDegraded)
    }
}
