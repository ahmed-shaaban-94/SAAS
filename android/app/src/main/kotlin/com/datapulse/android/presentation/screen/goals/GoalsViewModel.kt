package com.datapulse.android.presentation.screen.goals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.TargetSummary
import com.datapulse.android.domain.usecase.GetTargetSummaryUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class GoalsUiState(
    val targets: UiState<TargetSummary> = UiState.Loading,
    val isRefreshing: Boolean = false,
)

@HiltViewModel
class GoalsViewModel @Inject constructor(
    private val getTargetSummary: GetTargetSummaryUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(GoalsUiState())
    val state: StateFlow<GoalsUiState> = _state.asStateFlow()

    init {
        loadTargets()
    }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        loadTargets(forceRefresh = true)
    }

    private fun loadTargets(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getTargetSummary(forceRefresh = forceRefresh).collect { resource ->
                _state.value = _state.value.copy(
                    targets = resource.toUiState(),
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
