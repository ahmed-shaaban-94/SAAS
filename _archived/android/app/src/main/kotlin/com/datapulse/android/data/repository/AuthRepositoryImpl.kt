package com.datapulse.android.data.repository

import android.content.Intent
import com.datapulse.android.data.auth.AuthManager
import com.datapulse.android.domain.model.UserSession
import com.datapulse.android.domain.repository.AuthRepository
import kotlinx.coroutines.flow.Flow
import net.openid.appauth.AuthorizationResponse
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val authManager: AuthManager,
) : AuthRepository {

    override fun observeAuthState(): Flow<Boolean> = authManager.authState

    override suspend fun createLoginIntent(): Intent = authManager.createAuthIntent()

    override suspend fun handleLoginResponse(intent: Intent): UserSession {
        val response = AuthorizationResponse.fromIntent(intent)
            ?: throw RuntimeException("Authorization failed")
        val tokens = authManager.handleAuthResponse(response)
        val roles = authManager.extractUserRoles(tokens.accessToken)
        val claims = authManager.extractUserClaims(tokens.accessToken)
        return UserSession(
            sub = claims["sub"] ?: "",
            email = claims["email"] ?: "",
            preferredUsername = claims["preferred_username"] ?: "",
            tenantId = "1",
            roles = roles,
        )
    }

    override suspend fun logout() = authManager.signOut()

    override suspend fun isAuthenticated(): Boolean = authManager.isAuthenticated()

    override suspend fun getUserSession(): UserSession? {
        val token = authManager.getAccessToken() ?: return null
        val roles = authManager.extractUserRoles(token)
        val claims = authManager.extractUserClaims(token)
        return UserSession(
            sub = claims["sub"] ?: "",
            email = claims["email"] ?: "",
            preferredUsername = claims["preferred_username"] ?: "",
            tenantId = "1",
            roles = roles,
        )
    }
}
