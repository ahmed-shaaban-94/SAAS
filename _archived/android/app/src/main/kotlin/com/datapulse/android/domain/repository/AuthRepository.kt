package com.datapulse.android.domain.repository

import android.content.Intent
import com.datapulse.android.domain.model.UserSession
import kotlinx.coroutines.flow.Flow

interface AuthRepository {
    fun observeAuthState(): Flow<Boolean>
    suspend fun createLoginIntent(): Intent
    suspend fun handleLoginResponse(intent: Intent): UserSession
    suspend fun logout()
    suspend fun isAuthenticated(): Boolean
    suspend fun getUserSession(): UserSession?
}
