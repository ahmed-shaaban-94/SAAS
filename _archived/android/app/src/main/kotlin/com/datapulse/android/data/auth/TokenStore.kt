package com.datapulse.android.data.auth

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.tokenDataStore: DataStore<Preferences> by preferencesDataStore(name = "auth_tokens")

@Singleton
class TokenStore @Inject constructor(
    private val context: Context,
) {
    /** Reactive stream that emits true when an access token is present. */
    val hasAccessToken = context.tokenDataStore.data.map { it[ACCESS_TOKEN] != null }

    suspend fun getAccessToken(): String? =
        context.tokenDataStore.data.map { it[ACCESS_TOKEN] }.first()

    suspend fun getRefreshToken(): String? =
        context.tokenDataStore.data.map { it[REFRESH_TOKEN] }.first()

    suspend fun getIdToken(): String? =
        context.tokenDataStore.data.map { it[ID_TOKEN] }.first()

    suspend fun saveTokens(accessToken: String, refreshToken: String?, idToken: String?) {
        context.tokenDataStore.edit { prefs ->
            prefs[ACCESS_TOKEN] = accessToken
            refreshToken?.let { prefs[REFRESH_TOKEN] = it }
            idToken?.let { prefs[ID_TOKEN] = it }
        }
    }

    suspend fun clearTokens() {
        context.tokenDataStore.edit { it.clear() }
    }

    companion object {
        private val ACCESS_TOKEN = stringPreferencesKey("access_token")
        private val REFRESH_TOKEN = stringPreferencesKey("refresh_token")
        private val ID_TOKEN = stringPreferencesKey("id_token")
    }
}
