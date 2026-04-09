package com.datapulse.android.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.datapulse.android.presentation.navigation.DataPulseNavGraph
import com.datapulse.android.presentation.theme.DataPulseTheme
import org.junit.Rule
import org.junit.Test

class NavigationTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun unauthenticatedShowsLoginScreen() {
        composeTestRule.setContent {
            DataPulseTheme {
                DataPulseNavGraph(isAuthenticated = false)
            }
        }
        composeTestRule.onNodeWithText("Sign in with Auth0").assertIsDisplayed()
    }
}
