package com.datapulse.android.presentation.screen.explore

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.ExploreModelInfo
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetExploreModelsUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ExploreUiState(
    val models: UiState<List<ExploreModelInfo>> = UiState.Loading,
    val isRefreshing: Boolean = false,
)

@HiltViewModel
class ExploreViewModel @Inject constructor(
    private val getExploreModels: GetExploreModelsUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(ExploreUiState())
    val state: StateFlow<ExploreUiState> = _state.asStateFlow()

    init {
        loadModels()
    }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        loadModels(forceRefresh = true)
    }

    private fun loadModels(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getExploreModels(forceRefresh = forceRefresh).collect { resource ->
                _state.value = _state.value.copy(
                    models = resource.toUiState(),
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
