package com.datapulse.android.presentation.screen.explore

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.domain.model.ExploreModelInfo
import com.datapulse.android.presentation.common.EmptyState
import com.datapulse.android.presentation.common.ErrorState
import com.datapulse.android.presentation.common.PullRefreshWrapper
import com.datapulse.android.presentation.common.UiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExploreScreen(
    viewModel: ExploreViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    "Explore",
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
            when (val uiState = state.models) {
                is UiState.Loading -> {
                    Column(modifier = Modifier.padding(16.dp)) {
                        repeat(4) {
                            Card(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                                colors = CardDefaults.cardColors(
                                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
                                ),
                            ) {
                                Spacer(modifier = Modifier.height(80.dp))
                            }
                        }
                    }
                }
                is UiState.Empty -> EmptyState(message = "No explore models available")
                is UiState.Error -> ErrorState(
                    message = uiState.message,
                    onRetry = viewModel::refresh,
                )
                is UiState.Success -> {
                    LazyColumn(modifier = Modifier.padding(horizontal = 16.dp)) {
                        item {
                            Text(
                                "Data Models",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(vertical = 8.dp),
                            )
                        }
                        items(uiState.data) { model ->
                            ExploreModelCard(model)
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                        item { Spacer(modifier = Modifier.height(16.dp)) }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExploreModelCard(model: ExploreModelInfo) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                model.label,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
            )
            if (model.description != null) {
                Text(
                    model.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                )
            }
            Spacer(modifier = Modifier.height(8.dp))

            if (model.dimensions.isNotEmpty()) {
                Text(
                    "Dimensions (${model.dimensions.size})",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    model.dimensions.take(6).forEach { dim ->
                        AssistChip(
                            onClick = { },
                            label = { Text(dim.name, style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                    if (model.dimensions.size > 6) {
                        AssistChip(
                            onClick = { },
                            label = { Text("+${model.dimensions.size - 6} more", style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                }
            }

            if (model.metrics.isNotEmpty()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    "Metrics (${model.metrics.size})",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    model.metrics.take(6).forEach { metric ->
                        AssistChip(
                            onClick = { },
                            label = { Text(metric.name, style = MaterialTheme.typography.labelSmall) },
                        )
                    }
                }
            }
        }
    }
}
