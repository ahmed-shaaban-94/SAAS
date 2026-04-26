package com.datapulse.android.presentation.screen.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.data.preferences.UserPreferences
import com.datapulse.android.domain.model.UserSession
import com.datapulse.android.domain.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val isDarkMode: Boolean = true,
    val userSession: UserSession? = null,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val userPreferences: UserPreferences,
    private val authRepository: AuthRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            userPreferences.isDarkMode.collect { dark ->
                _state.value = _state.value.copy(isDarkMode = dark)
            }
        }
        viewModelScope.launch {
            val session = authRepository.getUserSession()
            _state.value = _state.value.copy(userSession = session)
        }
    }

    fun toggleDarkMode() {
        viewModelScope.launch {
            val newValue = !_state.value.isDarkMode
            userPreferences.setDarkMode(newValue)
        }
    }

    fun logout(onLoggedOut: () -> Unit) {
        viewModelScope.launch {
            authRepository.logout()
            onLoggedOut()
        }
    }
}
