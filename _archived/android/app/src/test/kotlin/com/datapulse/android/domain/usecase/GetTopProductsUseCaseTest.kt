package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.RankingItem
import com.datapulse.android.domain.model.RankingResult
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.AnalyticsRepository
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class GetTopProductsUseCaseTest {

    private val repository = mockk<AnalyticsRepository>()
    private val useCase = GetTopProductsUseCase(repository)

    @Test
    fun `invoke returns ranking result`() = runTest {
        val ranking = RankingResult(
            items = listOf(RankingItem(1, 10, "Drug A", 5000.0, 50.0)),
            total = 10000.0,
        )
        every { repository.getTopProducts(10, any(), any(), any()) } returns flowOf(Resource.Success(ranking))
        val results = useCase(limit = 10).toList()
        assertTrue(results[0] is Resource.Success)
        assertEquals(1, (results[0] as Resource.Success).data.items.size)
    }

    @Test
    fun `invoke with custom limit passes through`() = runTest {
        val ranking = RankingResult(emptyList(), 0.0)
        every { repository.getTopProducts(5, any(), any(), any()) } returns flowOf(Resource.Success(ranking))
        val results = useCase(limit = 5).toList()
        assertEquals(1, results.size)
    }
}
