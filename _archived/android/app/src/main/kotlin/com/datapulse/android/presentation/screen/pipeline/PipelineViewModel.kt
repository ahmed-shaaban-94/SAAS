package com.datapulse.android.presentation.screen.pipeline

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.QualityCheck
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetPipelineRunsUseCase
import com.datapulse.android.domain.usecase.GetQualityChecksUseCase
import com.datapulse.android.domain.usecase.TriggerPipelineUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class PipelineUiState(
    val runs: UiState<List<PipelineRun>> = UiState.Loading,
    val isTriggering: Boolean = false,
    val triggerError: String? = null,
    val isRefreshing: Boolean = false,
    val expandedRunId: String? = null,
    val qualityChecks: UiState<List<QualityCheck>> = UiState.Empty,
    val currentPage: Int = 1,
    val hasMorePages: Boolean = true,
    val isLoadingMore: Boolean = false,
)

@HiltViewModel
class PipelineViewModel @Inject constructor(
    private val getPipelineRuns: GetPipelineRunsUseCase,
    private val triggerPipeline: TriggerPipelineUseCase,
    private val getQualityChecks: GetQualityChecksUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(PipelineUiState())
    val state: StateFlow<PipelineUiState> = _state.asStateFlow()

    private var allRuns = mutableListOf<PipelineRun>()

    init { load() }

    fun refresh() {
        _state.value = _state.value.copy(isRefreshing = true)
        load(forceRefresh = true)
    }

    fun trigger() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isTriggering = true, triggerError = null)
            when (val result = triggerPipeline()) {
                is Resource.Success -> {
                    _state.value = _state.value.copy(isTriggering = false)
                    load(forceRefresh = true)
                }
                is Resource.Error -> {
                    _state.value = _state.value.copy(isTriggering = false, triggerError = result.message)
                }
                is Resource.Loading -> {}
            }
        }
    }

    fun clearTriggerError() {
        _state.value = _state.value.copy(triggerError = null)
    }

    fun toggleRunExpanded(runId: String) {
        val currentExpanded = _state.value.expandedRunId
        if (currentExpanded == runId) {
            _state.value = _state.value.copy(expandedRunId = null, qualityChecks = UiState.Empty)
        } else {
            _state.value = _state.value.copy(expandedRunId = runId, qualityChecks = UiState.Loading)
            loadQualityChecks(runId)
        }
    }

    private fun loadQualityChecks(runId: String) {
        viewModelScope.launch {
            getQualityChecks(runId).collect { resource ->
                _state.value = _state.value.copy(
                    qualityChecks = when (resource) {
                        is Resource.Loading -> UiState.Loading
                        is Resource.Success -> if (resource.data.isEmpty()) UiState.Empty else UiState.Success(resource.data)
                        is Resource.Error -> UiState.Error(resource.message)
                    },
                )
            }
        }
    }

    fun loadMore() {
        if (_state.value.isLoadingMore || !_state.value.hasMorePages) return
        _state.value = _state.value.copy(
            currentPage = _state.value.currentPage + 1,
            isLoadingMore = true,
        )
        load()
    }

    private fun load(forceRefresh: Boolean = false) {
        if (forceRefresh) {
            allRuns.clear()
            _state.value = _state.value.copy(currentPage = 1, hasMorePages = true)
        }
        viewModelScope.launch {
            getPipelineRuns(
                page = _state.value.currentPage,
                pageSize = PAGE_SIZE,
                forceRefresh = forceRefresh,
            ).collect { resource ->
                _state.value = _state.value.copy(
                    runs = when (resource) {
                        is Resource.Loading -> if (allRuns.isEmpty()) UiState.Loading else UiState.Success(allRuns.toList(), true)
                        is Resource.Success -> {
                            val newRuns = resource.data
                            if (_state.value.currentPage == 1) allRuns.clear()
                            allRuns.addAll(newRuns)
                            val hasMore = newRuns.size >= PAGE_SIZE
                            _state.value = _state.value.copy(hasMorePages = hasMore, isLoadingMore = false)
                            if (allRuns.isEmpty()) UiState.Empty else UiState.Success(allRuns.toList(), resource.fromCache)
                        }
                        is Resource.Error -> {
                            _state.value = _state.value.copy(isLoadingMore = false)
                            if (allRuns.isNotEmpty()) UiState.Success(allRuns.toList(), true) else UiState.Error(resource.message)
                        }
                    },
                    isRefreshing = if (resource !is Resource.Loading) false else _state.value.isRefreshing,
                )
            }
        }
    }

    companion object {
        private const val PAGE_SIZE = 20
    }
}
