package com.datapulse.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.datapulse.android.data.auth.AuthManager
import com.datapulse.android.data.preferences.UserPreferences
import com.datapulse.android.presentation.navigation.DataPulseNavGraph
import com.datapulse.android.presentation.theme.DataPulseTheme
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var userPreferences: UserPreferences
    @Inject lateinit var authManager: AuthManager

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val isDarkMode by userPreferences.isDarkMode.collectAsState(initial = true)
            val isAuthenticated by authManager.authState.collectAsState()
            DataPulseTheme(darkTheme = isDarkMode) {
                DataPulseNavGraph(isAuthenticated = isAuthenticated)
            }
        }
    }
}
