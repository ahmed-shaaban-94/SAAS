package com.datapulse.android.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.datapulse.android.presentation.screen.dashboard.DashboardScreen
import com.datapulse.android.presentation.theme.DataPulseTheme
import org.junit.Rule
import org.junit.Test

class DashboardScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun dashboardScreenShowsTitle() {
        composeTestRule.setContent {
            DataPulseTheme {
                DashboardScreen()
            }
        }
        composeTestRule.onNodeWithText("DataPulse").assertIsDisplayed()
    }
}
