package com.datapulse.android.domain.usecase

import android.content.Intent
import com.datapulse.android.domain.model.UserSession
import com.datapulse.android.domain.repository.AuthRepository
import javax.inject.Inject

class LoginUseCase @Inject constructor(
    private val repository: AuthRepository,
) {
    suspend fun createIntent(): Intent = repository.createLoginIntent()
    suspend fun handleResponse(intent: Intent): UserSession = repository.handleLoginResponse(intent)
}
