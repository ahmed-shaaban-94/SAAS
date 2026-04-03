package com.datapulse.android.presentation.screen.insights

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.AnomalyItem
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetAISummaryUseCase
import com.datapulse.android.domain.usecase.GetAnomaliesUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class InsightsUiState(
    val summary: UiState<String> = UiState.Loading,
    val anomalies: UiState<List<AnomalyItem>> = UiState.Loading,
    val isRefreshing: Boolean = false,
)

@HiltViewModel
class InsightsViewModel @Inject constructor(
    private val getAISummary: GetAISummaryUseCase,
    private val getAnomalies: GetAnomaliesUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(InsightsUiState())
    val state: StateFlow<InsightsUiState> = _state.asStateFlow()

    init {
        loadAll()
    }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        loadAll(forceRefresh = true)
    }

    private fun loadAll(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getAISummary(forceRefresh = forceRefresh).collect { resource ->
                _state.value = _state.value.copy(
                    summary = resource.toUiState(),
                    isRefreshing = if (resource !is Resource.Loading) false else _state.value.isRefreshing,
                )
            }
        }
        viewModelScope.launch {
            getAnomalies(forceRefresh = forceRefresh).collect { resource ->
                _state.value = _state.value.copy(anomalies = resource.toUiState())
            }
        }
    }

    private fun <T> Resource<T>.toUiState(): UiState<T> = when (this) {
        is Resource.Loading -> UiState.Loading
        is Resource.Success -> if (data == null) UiState.Empty else UiState.Success(data, fromCache)
        is Resource.Error -> UiState.Error(message)
    }
}
