package com.datapulse.android.di

import com.datapulse.android.BuildConfig
import com.datapulse.android.data.auth.AuthManager
import com.datapulse.android.data.remote.ApiService
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.auth.Auth
import io.ktor.client.plugins.auth.providers.BearerTokens
import io.ktor.client.plugins.auth.providers.bearer
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.plugins.logging.LogLevel
import io.ktor.client.plugins.logging.Logging
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        isLenient = true
    }

    @Provides
    @Singleton
    fun provideHttpClient(json: Json, authManager: AuthManager): HttpClient = HttpClient(OkHttp) {
        install(ContentNegotiation) {
            json(json)
        }

        install(Logging) {
            level = if (BuildConfig.DEBUG) LogLevel.BODY else LogLevel.NONE
        }

        install(Auth) {
            bearer {
                loadTokens {
                    val access = authManager.getAccessToken()
                    val refresh = authManager.getRefreshToken()
                    if (access != null) BearerTokens(access, refresh ?: "") else null
                }
                refreshTokens {
                    val newTokens = authManager.refreshTokens()
                    if (newTokens != null) {
                        BearerTokens(newTokens.accessToken, newTokens.refreshToken ?: "")
                    } else {
                        null
                    }
                }
            }
        }

        defaultRequest {
            url(BuildConfig.API_BASE_URL)
            contentType(ContentType.Application.Json)
        }
    }

    @Provides
    @Singleton
    fun provideApiService(client: HttpClient): ApiService = ApiService(client)
}
