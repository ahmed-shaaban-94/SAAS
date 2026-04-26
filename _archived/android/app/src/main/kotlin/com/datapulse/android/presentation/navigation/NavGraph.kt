package com.datapulse.android.presentation.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.datapulse.android.presentation.screen.alerts.AlertsScreen
import com.datapulse.android.presentation.screen.customers.CustomersScreen
import com.datapulse.android.presentation.screen.dashboard.DashboardScreen
import com.datapulse.android.presentation.screen.explore.ExploreScreen
import com.datapulse.android.presentation.screen.goals.GoalsScreen
import com.datapulse.android.presentation.screen.insights.InsightsScreen
import com.datapulse.android.presentation.screen.login.LoginScreen
import com.datapulse.android.presentation.screen.pipeline.PipelineScreen
import com.datapulse.android.presentation.screen.products.ProductsScreen
import com.datapulse.android.presentation.screen.reports.ReportsScreen
import com.datapulse.android.presentation.screen.returns.ReturnsScreen
import com.datapulse.android.presentation.screen.sites.SitesScreen
import com.datapulse.android.presentation.screen.settings.SettingsScreen
import com.datapulse.android.presentation.screen.sqllab.SqlLabScreen
import com.datapulse.android.presentation.screen.staff.StaffScreen

@Composable
fun DataPulseNavGraph(
    navController: NavHostController = rememberNavController(),
    isAuthenticated: Boolean = false,
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = when (navBackStackEntry?.destination?.route) {
        NavRoute.Dashboard::class.qualifiedName -> NavRoute.Dashboard
        NavRoute.Products::class.qualifiedName -> NavRoute.Products
        NavRoute.Customers::class.qualifiedName -> NavRoute.Customers
        NavRoute.Staff::class.qualifiedName -> NavRoute.Staff
        NavRoute.Sites::class.qualifiedName -> NavRoute.Sites
        NavRoute.Returns::class.qualifiedName -> NavRoute.Returns
        NavRoute.Pipeline::class.qualifiedName -> NavRoute.Pipeline
        NavRoute.Settings::class.qualifiedName -> NavRoute.Settings
        NavRoute.Goals::class.qualifiedName -> NavRoute.Goals
        NavRoute.Alerts::class.qualifiedName -> NavRoute.Alerts
        NavRoute.Insights::class.qualifiedName -> NavRoute.Insights
        NavRoute.SqlLab::class.qualifiedName -> NavRoute.SqlLab
        NavRoute.Reports::class.qualifiedName -> NavRoute.Reports
        NavRoute.Explore::class.qualifiedName -> NavRoute.Explore
        else -> null
    }

    val startDestination: Any = if (isAuthenticated) NavRoute.Dashboard else NavRoute.Login
    val showBottomBar = isAuthenticated && currentRoute != null

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                BottomNavBar(
                    currentRoute = currentRoute,
                    onNavigate = { route ->
                        navController.navigate(route) {
                            popUpTo(NavRoute.Dashboard) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                )
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable<NavRoute.Login> {
                LoginScreen(
                    onLoginSuccess = {
                        navController.navigate(NavRoute.Dashboard) {
                            popUpTo(NavRoute.Login) { inclusive = true }
                        }
                    },
                )
            }
            composable<NavRoute.Dashboard> { DashboardScreen() }
            composable<NavRoute.Products> { ProductsScreen() }
            composable<NavRoute.Customers> { CustomersScreen() }
            composable<NavRoute.Staff> { StaffScreen() }
            composable<NavRoute.Sites> { SitesScreen() }
            composable<NavRoute.Returns> { ReturnsScreen() }
            composable<NavRoute.Pipeline> { PipelineScreen() }
            composable<NavRoute.Goals> { GoalsScreen() }
            composable<NavRoute.Alerts> { AlertsScreen() }
            composable<NavRoute.Insights> { InsightsScreen() }
            composable<NavRoute.SqlLab> { SqlLabScreen() }
            composable<NavRoute.Reports> { ReportsScreen() }
            composable<NavRoute.Explore> { ExploreScreen() }
            composable<NavRoute.Settings> {
                SettingsScreen(
                    onLoggedOut = {
                        navController.navigate(NavRoute.Login) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                )
            }
        }
    }
}
