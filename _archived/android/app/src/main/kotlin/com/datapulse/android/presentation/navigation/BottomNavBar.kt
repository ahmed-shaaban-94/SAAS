package com.datapulse.android.presentation.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Dashboard
import androidx.compose.material.icons.outlined.Inventory2
import androidx.compose.material.icons.outlined.MoreHoriz
import androidx.compose.material.icons.outlined.People
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import com.datapulse.android.R
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.LocationOn
import androidx.compose.material.icons.outlined.AssignmentReturn
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Terminal
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

data class BottomNavItem(
    val route: NavRoute,
    val icon: ImageVector,
    val labelResId: Int,
)

val primaryNavItems = listOf(
    BottomNavItem(NavRoute.Dashboard, Icons.Outlined.Dashboard, R.string.nav_dashboard),
    BottomNavItem(NavRoute.Products, Icons.Outlined.Inventory2, R.string.nav_products),
    BottomNavItem(NavRoute.Customers, Icons.Outlined.People, R.string.nav_customers),
)

val moreNavItems = listOf(
    BottomNavItem(NavRoute.Staff, Icons.Outlined.Person, R.string.nav_staff),
    BottomNavItem(NavRoute.Sites, Icons.Outlined.LocationOn, R.string.nav_sites),
    BottomNavItem(NavRoute.Returns, Icons.Outlined.AssignmentReturn, R.string.nav_returns),
    BottomNavItem(NavRoute.Pipeline, Icons.Outlined.Terminal, R.string.nav_pipeline),
    BottomNavItem(NavRoute.Settings, Icons.Outlined.Settings, R.string.nav_settings),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BottomNavBar(
    currentRoute: NavRoute?,
    onNavigate: (NavRoute) -> Unit,
) {
    var showMoreSheet by remember { mutableStateOf(false) }

    NavigationBar {
        primaryNavItems.forEach { item ->
            NavigationBarItem(
                icon = { Icon(item.icon, contentDescription = stringResource(item.labelResId)) },
                label = { Text(stringResource(item.labelResId)) },
                selected = currentRoute == item.route,
                onClick = { onNavigate(item.route) },
            )
        }
        NavigationBarItem(
            icon = { Icon(Icons.Outlined.MoreHoriz, contentDescription = stringResource(R.string.nav_more)) },
            label = { Text(stringResource(R.string.nav_more)) },
            selected = moreNavItems.any { it.route == currentRoute },
            onClick = { showMoreSheet = true },
        )
    }

    if (showMoreSheet) {
        ModalBottomSheet(
            onDismissRequest = { showMoreSheet = false },
            sheetState = rememberModalBottomSheetState(),
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 32.dp),
            ) {
                moreNavItems.forEach { item ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                onNavigate(item.route)
                                showMoreSheet = false
                            }
                            .padding(horizontal = 24.dp, vertical = 16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Icon(
                            imageVector = item.icon,
                            contentDescription = null,
                            tint = if (currentRoute == item.route) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            },
                        )
                        Spacer(modifier = Modifier.width(16.dp))
                        Text(
                            text = stringResource(item.labelResId),
                            style = MaterialTheme.typography.bodyLarge,
                            color = if (currentRoute == item.route) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface
                            },
                        )
                    }
                }
            }
        }
    }
}
