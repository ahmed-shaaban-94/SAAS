package com.datapulse.android.presentation.common

sealed interface UiState<out T> {
    data object Loading : UiState<Nothing>
    data class Success<T>(val data: T, val fromCache: Boolean = false) : UiState<T>
    data class Error(val message: String, val cached: Any? = null) : UiState<Nothing>
    data object Empty : UiState<Nothing>
}
