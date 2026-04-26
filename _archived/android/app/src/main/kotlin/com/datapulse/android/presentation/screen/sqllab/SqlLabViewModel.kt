package com.datapulse.android.presentation.screen.sqllab

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.ExecuteQueryUseCase
import com.datapulse.android.presentation.common.UiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class QueryResult(
    val columns: List<String>,
    val rows: List<List<String>>,
)

data class SqlLabUiState(
    val query: String = "",
    val results: UiState<QueryResult> = UiState.Empty,
)

@HiltViewModel
class SqlLabViewModel @Inject constructor(
    private val executeQuery: ExecuteQueryUseCase,
) : ViewModel() {

    private val _state = MutableStateFlow(SqlLabUiState())
    val state: StateFlow<SqlLabUiState> = _state.asStateFlow()

    fun updateQuery(query: String) {
        _state.value = _state.value.copy(query = query)
    }

    fun execute() {
        val query = _state.value.query.trim()
        if (query.isBlank()) return

        _state.value = _state.value.copy(results = UiState.Loading)

        viewModelScope.launch {
            executeQuery(query).collect { resource ->
                _state.value = _state.value.copy(
                    results = when (resource) {
                        is Resource.Loading -> UiState.Loading
                        is Resource.Success -> {
                            if (resource.data == null) UiState.Empty
                            else UiState.Success(resource.data, resource.fromCache)
                        }
                        is Resource.Error -> UiState.Error(resource.message)
                    },
                )
            }
        }
    }
}
