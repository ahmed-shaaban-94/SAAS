package com.datapulse.android.presentation.screen.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.HealthStatus
import com.datapulse.android.domain.model.KpiSummary
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.TrendResult
import com.datapulse.android.domain.usecase.GetDailyTrendUseCase
import com.datapulse.android.domain.usecase.GetDashboardUseCase
import com.datapulse.android.domain.usecase.GetHealthUseCase
import com.datapulse.android.domain.usecase.GetMonthlyTrendUseCase
import com.datapulse.android.presentation.common.UiState
import com.datapulse.android.presentation.util.DatePreset
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val kpi: UiState<KpiSummary> = UiState.Loading,
    val dailyTrend: UiState<TrendResult> = UiState.Loading,
    val monthlyTrend: UiState<TrendResult> = UiState.Loading,
    val health: HealthStatus? = null,
    val isRefreshing: Boolean = false,
    val selectedPreset: String = "All",
    val startDate: String? = null,
    val endDate: String? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val getDashboard: GetDashboardUseCase,
    private val getDailyTrend: GetDailyTrendUseCase,
    private val getMonthlyTrend: GetMonthlyTrendUseCase,
    private val getHealth: GetHealthUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        loadAll()
        startHealthPolling()
    }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        loadAll(forceRefresh = true)
    }

    fun selectPreset(preset: DatePreset) {
        val start = preset.startDate.ifBlank { null }
        val end = preset.endDate.ifBlank { null }
        _state.value = _state.value.copy(
            selectedPreset = preset.label,
            startDate = start,
            endDate = end,
        )
        loadAll(forceRefresh = true)
    }

    private fun loadAll(forceRefresh: Boolean = false) {
        loadKpi(forceRefresh)
        loadDailyTrend(forceRefresh)
        loadMonthlyTrend(forceRefresh)
    }

    private fun loadKpi(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getDashboard(
                startDate = _state.value.startDate,
                endDate = _state.value.endDate,
                forceRefresh = forceRefresh,
            ).collect { resource ->
                _state.value = _state.value.copy(
                    kpi = resource.toUiState(),
                    isRefreshing = if (resource !is Resource.Loading) false else _state.value.isRefreshing,
                )
            }
        }
    }

    private fun loadDailyTrend(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getDailyTrend(
                startDate = _state.value.startDate,
                endDate = _state.value.endDate,
                forceRefresh = forceRefresh,
            ).collect { resource ->
                _state.value = _state.value.copy(dailyTrend = resource.toUiState())
            }
        }
    }

    private fun loadMonthlyTrend(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getMonthlyTrend(
                startDate = _state.value.startDate,
                endDate = _state.value.endDate,
                forceRefresh = forceRefresh,
            ).collect { resource ->
                _state.value = _state.value.copy(monthlyTrend = resource.toUiState())
            }
        }
    }

    private fun startHealthPolling() {
        viewModelScope.launch {
            while (true) {
                getHealth().collect { resource ->
                    if (resource is Resource.Success) {
                        _state.value = _state.value.copy(health = resource.data)
                    }
                }
                delay(30_000)
            }
        }
    }

    private fun <T> Resource<T>.toUiState(): UiState<T> = when (this) {
        is Resource.Loading -> UiState.Loading
        is Resource.Success -> if (data == null) UiState.Empty else UiState.Success(data, fromCache)
        is Resource.Error -> UiState.Error(message)
    }
}
