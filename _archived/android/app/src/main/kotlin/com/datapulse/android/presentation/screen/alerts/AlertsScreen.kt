package com.datapulse.android.presentation.screen.alerts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.domain.model.AlertLogItem
import com.datapulse.android.presentation.common.EmptyState
import com.datapulse.android.presentation.common.ErrorState
import com.datapulse.android.presentation.common.PullRefreshWrapper
import com.datapulse.android.presentation.common.UiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertsScreen(
    viewModel: AlertsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    "Alerts",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        PullRefreshWrapper(
            isRefreshing = state.isRefreshing,
            onRefresh = viewModel::refresh,
        ) {
            when (val uiState = state.alerts) {
                is UiState.Loading -> {
                    Column(modifier = Modifier.padding(16.dp)) {
                        repeat(5) {
                            Card(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                                ),
                            ) {
                                Spacer(modifier = Modifier.height(64.dp))
                            }
                        }
                    }
                }
                is UiState.Empty -> EmptyState(message = "No alerts — everything looks good!")
                is UiState.Error -> ErrorState(
                    message = uiState.message,
                    onRetry = viewModel::refresh,
                )
                is UiState.Success -> {
                    LazyColumn(modifier = Modifier.padding(horizontal = 16.dp)) {
                        items(uiState.data) { alert ->
                            AlertCard(
                                alert = alert,
                                onAcknowledge = { viewModel.acknowledge(alert.id) },
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                        item { Spacer(modifier = Modifier.height(16.dp)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun AlertCard(
    alert: AlertLogItem,
    onAcknowledge: () -> Unit,
) {
    val isAcknowledged = alert.acknowledgedAt != null
    val containerColor = when (alert.severity) {
        "critical" -> MaterialTheme.colorScheme.errorContainer
        "warning" -> MaterialTheme.colorScheme.tertiaryContainer
        else -> MaterialTheme.colorScheme.surfaceVariant
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = containerColor),
    ) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Row(
                modifier = Modifier.weight(1f),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = alert.severity,
                    modifier = Modifier.size(20.dp),
                    tint = if (alert.severity == "critical")
                        MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.tertiary,
                )
                Column {
                    Text(
                        alert.alertType,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        alert.message,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        alert.createdAt,
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                    )
                }
            }
            if (!isAcknowledged) {
                IconButton(onClick = onAcknowledge) {
                    Icon(
                        Icons.Default.Check,
                        contentDescription = "Acknowledge",
                        tint = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
    }
}
