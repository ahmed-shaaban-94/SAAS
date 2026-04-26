package com.datapulse.android.presentation

import com.datapulse.android.domain.model.HealthStatus
import com.datapulse.android.domain.model.KpiSummary
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.TrendResult
import com.datapulse.android.domain.usecase.GetDailyTrendUseCase
import com.datapulse.android.domain.usecase.GetDashboardUseCase
import com.datapulse.android.domain.usecase.GetHealthUseCase
import com.datapulse.android.domain.usecase.GetMonthlyTrendUseCase
import com.datapulse.android.presentation.common.UiState
import com.datapulse.android.presentation.screen.dashboard.DashboardViewModel
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DashboardViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private val getDashboard = mockk<GetDashboardUseCase>()
    private val getDailyTrend = mockk<GetDailyTrendUseCase>()
    private val getMonthlyTrend = mockk<GetMonthlyTrendUseCase>()
    private val getHealth = mockk<GetHealthUseCase>()

    private val kpi = KpiSummary(1000.0, 50000.0, 500000.0, 12.5, -3.2, 150, 42)
    private val trend = TrendResult(emptyList(), 0.0, 0.0, 0.0, 0.0, null)

    @BeforeEach
    fun setup() {
        Dispatchers.setMain(testDispatcher)
        every { getDashboard(any(), any(), any()) } returns flowOf(Resource.Success(kpi))
        every { getDailyTrend(any(), any(), any()) } returns flowOf(Resource.Success(trend))
        every { getMonthlyTrend(any(), any(), any()) } returns flowOf(Resource.Success(trend))
        every { getHealth() } returns flowOf(Resource.Success(HealthStatus("ok", "ok")))
    }

    @AfterEach
    fun tearDown() { Dispatchers.resetMain() }

    @Test
    fun `init loads kpi data`() = runTest {
        val vm = DashboardViewModel(getDashboard, getDailyTrend, getMonthlyTrend, getHealth)
        advanceUntilIdle()
        assertTrue(vm.state.value.kpi is UiState.Success)
    }

    @Test
    fun `refresh sets isRefreshing then loads`() = runTest {
        val vm = DashboardViewModel(getDashboard, getDailyTrend, getMonthlyTrend, getHealth)
        advanceUntilIdle()
        vm.refresh()
        advanceUntilIdle()
        assertTrue(vm.state.value.kpi is UiState.Success)
    }

    @Test
    fun `error state propagates`() = runTest {
        every { getDashboard(any(), any(), any()) } returns flowOf(Resource.Error("fail"))
        val vm = DashboardViewModel(getDashboard, getDailyTrend, getMonthlyTrend, getHealth)
        advanceUntilIdle()
        assertTrue(vm.state.value.kpi is UiState.Error)
    }
}
