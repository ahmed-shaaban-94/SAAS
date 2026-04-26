package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.KpiSummary
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

class GetDashboardUseCaseTest {

    private val repository = mockk<AnalyticsRepository>()
    private val useCase = GetDashboardUseCase(repository)

    private val kpi = KpiSummary(1000.0, 50000.0, 500000.0, 12.5, -3.2, 150, 42)

    @Test
    fun `invoke returns success from repository`() = runTest {
        every { repository.getSummary(any(), any(), any()) } returns flowOf(Resource.Success(kpi))
        val results = useCase().toList()
        assertEquals(1, results.size)
        assertTrue(results[0] is Resource.Success)
        assertEquals(kpi, (results[0] as Resource.Success).data)
    }

    @Test
    fun `invoke returns error from repository`() = runTest {
        every { repository.getSummary(any(), any(), any()) } returns flowOf(Resource.Error("Network error"))
        val results = useCase().toList()
        assertTrue(results[0] is Resource.Error)
        assertEquals("Network error", (results[0] as Resource.Error).message)
    }

    @Test
    fun `invoke passes date params to repository`() = runTest {
        every { repository.getSummary("2024-01-01", "2024-01-31", false) } returns flowOf(Resource.Success(kpi))
        val results = useCase(startDate = "2024-01-01", endDate = "2024-01-31").toList()
        assertEquals(1, results.size)
    }
}
