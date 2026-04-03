package com.datapulse.android.presentation.screen.alerts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.AlertLogItem
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetAlertLogUseCase
import com.datapulse.android.domain.usecase.AcknowledgeAlertUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AlertsUiState(
    val alerts: UiState<List<AlertLogItem>> = UiState.Loading,
    val isRefreshing: Boolean = false,
)

@HiltViewModel
class AlertsViewModel @Inject constructor(
    private val getAlertLog: GetAlertLogUseCase,
    private val acknowledgeAlert: AcknowledgeAlertUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(AlertsUiState())
    val state: StateFlow<AlertsUiState> = _state.asStateFlow()

    init {
        loadAlerts()
    }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        loadAlerts(forceRefresh = true)
    }

    fun acknowledge(alertId: Int) {
        viewModelScope.launch {
            acknowledgeAlert(alertId)
            loadAlerts(forceRefresh = true)
        }
    }

    private fun loadAlerts(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getAlertLog(forceRefresh = forceRefresh).collect { resource ->
                _state.value = _state.value.copy(
                    alerts = resource.toUiState(),
                    isRefreshing = if (resource !is Resource.Loading) false else _state.value.isRefreshing,
                )
            }
        }
    }

    private fun <T> Resource<T>.toUiState(): UiState<T> = when (this) {
        is Resource.Loading -> UiState.Loading
        is Resource.Success -> if (data == null) UiState.Empty else UiState.Success(data, fromCache)
        is Resource.Error -> UiState.Error(message)
    }
}
