package com.datapulse.android.data.auth

import android.content.Context
import android.content.Intent
import android.net.Uri
import com.datapulse.android.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.withContext
import net.openid.appauth.AuthorizationRequest
import net.openid.appauth.AuthorizationResponse
import net.openid.appauth.AuthorizationService
import net.openid.appauth.AuthorizationServiceConfiguration
import net.openid.appauth.ResponseTypeValues
import net.openid.appauth.TokenResponse
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

data class AuthTokens(
    val accessToken: String,
    val refreshToken: String?,
    val idToken: String?,
)

@Singleton
class AuthManager @Inject constructor(
    private val context: Context,
    private val tokenStore: TokenStore,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val authService = AuthorizationService(context)

    /** Reactive auth state — emits true when user has a valid access token. */
    val authState: StateFlow<Boolean> = tokenStore.hasAccessToken
        .stateIn(scope, SharingStarted.Eagerly, false)

    private val serviceConfig = AuthorizationServiceConfiguration(
        Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/auth"),
        Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/token"),
        null,
        Uri.parse("${BuildConfig.KEYCLOAK_URL}/protocol/openid-connect/logout"),
    )

    fun createAuthIntent(): Intent {
        val authRequest = AuthorizationRequest.Builder(
            serviceConfig,
            CLIENT_ID,
            ResponseTypeValues.CODE,
            Uri.parse(REDIRECT_URI),
        )
            .setScope("openid email profile")
            .build()

        return authService.getAuthorizationRequestIntent(authRequest)
    }

    suspend fun handleAuthResponse(response: AuthorizationResponse): AuthTokens =
        withContext(Dispatchers.IO) {
            suspendCoroutine { cont ->
                authService.performTokenRequest(response.createTokenExchangeRequest()) { tokenResponse, exception ->
                    if (tokenResponse != null) {
                        val tokens = AuthTokens(
                            accessToken = tokenResponse.accessToken ?: "",
                            refreshToken = tokenResponse.refreshToken,
                            idToken = tokenResponse.idToken,
                        )
                        cont.resume(tokens)
                    } else {
                        cont.resumeWithException(
                            exception ?: RuntimeException("Token exchange failed")
                        )
                    }
                }
            }
        }.also { tokens ->
            tokenStore.saveTokens(tokens.accessToken, tokens.refreshToken, tokens.idToken)
        }

    suspend fun refreshTokens(): AuthTokens? = withContext(Dispatchers.IO) {
        val refreshToken = tokenStore.getRefreshToken() ?: return@withContext null
        try {
            suspendCoroutine<TokenResponse?> { cont ->
                val tokenRequest = net.openid.appauth.TokenRequest.Builder(
                    serviceConfig,
                    CLIENT_ID,
                )
                    .setGrantType("refresh_token")
                    .setRefreshToken(refreshToken)
                    .build()

                authService.performTokenRequest(tokenRequest) { tokenResponse, _ ->
                    cont.resume(tokenResponse)
                }
            }?.let { tokenResponse ->
                val tokens = AuthTokens(
                    accessToken = tokenResponse.accessToken ?: "",
                    refreshToken = tokenResponse.refreshToken,
                    idToken = tokenResponse.idToken,
                )
                tokenStore.saveTokens(tokens.accessToken, tokens.refreshToken, tokens.idToken)
                tokens
            }
        } catch (_: Exception) {
            null
        }
    }

    suspend fun getAccessToken(): String? = tokenStore.getAccessToken()

    suspend fun getRefreshToken(): String? = tokenStore.getRefreshToken()

    suspend fun isAuthenticated(): Boolean = tokenStore.getAccessToken() != null

    suspend fun signOut() {
        tokenStore.clearTokens()
    }

    fun extractUserRoles(accessToken: String): List<String> {
        return try {
            val parts = accessToken.split(".")
            if (parts.size != 3) return emptyList()
            val payload = String(android.util.Base64.decode(parts[1], android.util.Base64.URL_SAFE))
            val realmAccess = kotlinx.serialization.json.Json.parseToJsonElement(payload)
                .jsonObject["realm_access"]
                ?.jsonObject?.get("roles")
                ?.jsonArray
                ?.map { it.jsonPrimitive.content }
            realmAccess ?: emptyList()
        } catch (_: Exception) {
            emptyList()
        }
    }

    fun extractUserClaims(accessToken: String): Map<String, String> {
        return try {
            val parts = accessToken.split(".")
            if (parts.size != 3) return emptyMap()
            val payload = String(android.util.Base64.decode(parts[1], android.util.Base64.URL_SAFE))
            val json = kotlinx.serialization.json.Json.parseToJsonElement(payload).jsonObject
            mapOf(
                "sub" to (json["sub"]?.jsonPrimitive?.content ?: ""),
                "email" to (json["email"]?.jsonPrimitive?.content ?: ""),
                "preferred_username" to (json["preferred_username"]?.jsonPrimitive?.content ?: ""),
            )
        } catch (_: Exception) {
            emptyMap()
        }
    }

    companion object {
        private const val CLIENT_ID = "datapulse-frontend"
        private const val REDIRECT_URI = "com.datapulse.android:/oauth2callback"
    }
}
