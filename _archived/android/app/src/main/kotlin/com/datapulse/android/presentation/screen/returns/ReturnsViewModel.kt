package com.datapulse.android.presentation.screen.returns

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.ReturnAnalysis
import com.datapulse.android.domain.usecase.GetReturnsUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class ReturnsViewModel @Inject constructor(
    private val getReturns: GetReturnsUseCase,
) : ViewModel() {
    private val _state = MutableStateFlow<UiState<List<ReturnAnalysis>>>(UiState.Loading)
    val state: StateFlow<UiState<List<ReturnAnalysis>>> = _state.asStateFlow()
    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init { load() }

    fun refresh() { _isRefreshing.value = true; load(forceRefresh = true) }

    private fun load(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getReturns(forceRefresh = forceRefresh).collect { resource ->
                _state.value = when (resource) {
                    is Resource.Loading -> UiState.Loading
                    is Resource.Success -> if (resource.data.isEmpty()) UiState.Empty else UiState.Success(resource.data, resource.fromCache)
                    is Resource.Error -> UiState.Error(resource.message)
                }
                if (resource !is Resource.Loading) _isRefreshing.value = false
            }
        }
    }
}
