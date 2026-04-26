package com.datapulse.android.presentation.screen.customers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.RankingResult
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetTopCustomersUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CustomersViewModel @Inject constructor(
    private val getTopCustomers: GetTopCustomersUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow<UiState<RankingResult>>(UiState.Loading)
    val state: StateFlow<UiState<RankingResult>> = _state.asStateFlow()

    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init { load() }

    fun refresh() {
        _isRefreshing.value = true
        load(forceRefresh = true)
    }

    private fun load(forceRefresh: Boolean = false) {
        viewModelScope.launch {
            getTopCustomers(forceRefresh = forceRefresh).collect { resource ->
                _state.value = when (resource) {
                    is Resource.Loading -> UiState.Loading
                    is Resource.Success -> if (resource.data.items.isEmpty()) UiState.Empty else UiState.Success(resource.data, resource.fromCache)
                    is Resource.Error -> UiState.Error(resource.message)
                }
                if (resource !is Resource.Loading) _isRefreshing.value = false
            }
        }
    }
}
