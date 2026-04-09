package com.datapulse.android.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import com.datapulse.android.presentation.screen.login.LoginScreen
import com.datapulse.android.presentation.theme.DataPulseTheme
import org.junit.Rule
import org.junit.Test

class LoginScreenTest {

    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun loginScreenShowsTitleAndButton() {
        composeTestRule.setContent {
            DataPulseTheme {
                LoginScreen()
            }
        }
        composeTestRule.onNodeWithText("DataPulse").assertIsDisplayed()
        composeTestRule.onNodeWithText("Business Analytics").assertIsDisplayed()
        composeTestRule.onNodeWithText("Sign in with Auth0").assertIsDisplayed()
    }
}
