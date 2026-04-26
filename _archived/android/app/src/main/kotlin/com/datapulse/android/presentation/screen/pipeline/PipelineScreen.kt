package com.datapulse.android.presentation.screen.pipeline

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.AlertDialog
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.FabPosition
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.R
import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.QualityCheck
import com.datapulse.android.presentation.common.*
import com.datapulse.android.presentation.util.formatDuration
import com.datapulse.android.presentation.util.formatNumber
import com.datapulse.android.presentation.util.formatRelativeTime

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PipelineScreen(viewModel: PipelineViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }
    var showConfirmDialog by remember { mutableStateOf(false) }

    LaunchedEffect(state.triggerError) {
        state.triggerError?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearTriggerError()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Pipeline", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
            )
        },
        floatingActionButton = {
            ExtendedFloatingActionButton(
                onClick = { showConfirmDialog = true },
                icon = { Icon(Icons.Filled.PlayArrow, contentDescription = null) },
                text = { Text(stringResource(R.string.pipeline_trigger)) },
            )
        },
        floatingActionButtonPosition = FabPosition.End,
        snackbarHost = { SnackbarHost(snackbarHostState) },
    ) { padding ->
        PullRefreshWrapper(
            isRefreshing = state.isRefreshing,
            onRefresh = { viewModel.refresh() },
            modifier = Modifier.padding(padding),
        ) {
            when (val runs = state.runs) {
                is UiState.Loading -> Column { repeat(5) { ListItemSkeleton() } }
                is UiState.Error -> ErrorState(message = runs.message, onRetry = { viewModel.refresh() })
                is UiState.Empty -> EmptyState(message = "No pipeline runs yet")
                is UiState.Success -> {
                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                        val latestRun = runs.data.firstOrNull()
                        if (latestRun != null) {
                            item {
                                Text(
                                    text = "Latest Run",
                                    style = MaterialTheme.typography.titleMedium,
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                )
                                LatestRunCard(run = latestRun)
                                Spacer(modifier = Modifier.height(16.dp))
                                Text(
                                    text = "Run History",
                                    style = MaterialTheme.typography.titleMedium,
                                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                                )
                            }
                        }
                        items(runs.data) { run ->
                            RunHistoryItem(
                                run = run,
                                isExpanded = state.expandedRunId == run.id,
                                qualityChecks = if (state.expandedRunId == run.id) state.qualityChecks else null,
                                onClick = { viewModel.toggleRunExpanded(run.id) },
                            )
                        }
                        if (state.hasMorePages) {
                            item {
                                LaunchedEffect(Unit) {
                                    viewModel.loadMore()
                                }
                                if (state.isLoadingMore) {
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(16.dp),
                                        contentAlignment = Alignment.Center,
                                    ) {
                                        CircularProgressIndicator(modifier = Modifier.size(24.dp))
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showConfirmDialog = false },
            title = { Text(stringResource(R.string.pipeline_confirm_title)) },
            text = { Text(stringResource(R.string.pipeline_confirm_message)) },
            confirmButton = {
                TextButton(onClick = {
                    showConfirmDialog = false
                    viewModel.trigger()
                }) { Text(stringResource(R.string.pipeline_confirm_yes)) }
            },
            dismissButton = {
                TextButton(onClick = { showConfirmDialog = false }) {
                    Text(stringResource(R.string.pipeline_confirm_no))
                }
            },
        )
    }
}

@Composable
private fun LatestRunCard(run: PipelineRun) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Status", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                StatusBadge(status = run.status)
            }
            Spacer(modifier = Modifier.height(8.dp))
            InfoRow("Type", run.runType)
            run.durationSeconds?.let { InfoRow("Duration", formatDuration(it)) }
            run.rowsLoaded?.let { InfoRow("Rows", formatNumber(it)) }
            InfoRow("Started", formatRelativeTime(run.startedAt))
        }
    }
}

@Composable
private fun RunHistoryItem(
    run: PipelineRun,
    isExpanded: Boolean = false,
    qualityChecks: UiState<List<QualityCheck>>? = null,
    onClick: () -> Unit = {},
) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        onClick = onClick,
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "#${run.id.take(8)}",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                    )
                    Text(
                        text = "${run.runType} - ${formatRelativeTime(run.startedAt)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                StatusBadge(status = run.status)
            }

            AnimatedVisibility(visible = isExpanded && qualityChecks != null) {
                if (qualityChecks != null) {
                    Column {
                        Spacer(modifier = Modifier.height(8.dp))
                        HorizontalDivider()
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Quality Checks",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold,
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        when (qualityChecks) {
                            is UiState.Loading -> {
                                Text(
                                    text = "Loading...",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            is UiState.Empty -> {
                                Text(
                                    text = "No quality checks",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            is UiState.Error -> {
                                Text(
                                    text = qualityChecks.message,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                            is UiState.Success -> {
                                qualityChecks.data.forEach { check ->
                                    QualityCheckRow(check)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun QualityCheckRow(check: QualityCheck) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = if (check.passed) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
            contentDescription = null,
            modifier = Modifier.size(16.dp),
            tint = if (check.passed) {
                MaterialTheme.colorScheme.primary
            } else {
                MaterialTheme.colorScheme.error
            },
        )
        Spacer(modifier = Modifier.width(8.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = check.checkName,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = "${check.stage} - ${check.severity}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
    }
}
