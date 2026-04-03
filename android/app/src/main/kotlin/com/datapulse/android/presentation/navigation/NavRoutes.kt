package com.datapulse.android.presentation.navigation

import kotlinx.serialization.Serializable

sealed interface NavRoute {
    @Serializable data object Login : NavRoute
    @Serializable data object Dashboard : NavRoute
    @Serializable data object Products : NavRoute
    @Serializable data object Customers : NavRoute
    @Serializable data object Staff : NavRoute
    @Serializable data object Sites : NavRoute
    @Serializable data object Returns : NavRoute
    @Serializable data object Pipeline : NavRoute
    @Serializable data object Settings : NavRoute
    @Serializable data object Goals : NavRoute
    @Serializable data object Alerts : NavRoute
    @Serializable data object Insights : NavRoute
    @Serializable data object SqlLab : NavRoute
    @Serializable data object Reports : NavRoute
    @Serializable data object Explore : NavRoute
}
