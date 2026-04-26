package com.datapulse.android.presentation.screen.returns

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.domain.model.ReturnAnalysis
import com.datapulse.android.presentation.common.*
import com.datapulse.android.presentation.util.formatCompact
import com.datapulse.android.presentation.util.formatNumber

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReturnsScreen(viewModel: ReturnsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val isRefreshing by viewModel.isRefreshing.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Returns Analysis", fontWeight = FontWeight.Bold) },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
        )
        PullRefreshWrapper(isRefreshing = isRefreshing, onRefresh = { viewModel.refresh() }) {
            when (val s = state) {
                is UiState.Loading -> Column { repeat(8) { ListItemSkeleton() } }
                is UiState.Error -> ErrorState(message = s.message, onRetry = { viewModel.refresh() })
                is UiState.Empty -> EmptyState()
                is UiState.Success -> {
                    LazyColumn(modifier = Modifier.fillMaxSize()) {
                        item {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text("Drug", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1.5f))
                                Text("Customer", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1.5f))
                                Text("Qty", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(0.7f))
                                Text("Amount", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(1f))
                                Text("Count", style = MaterialTheme.typography.labelMedium, modifier = Modifier.weight(0.6f))
                            }
                            HorizontalDivider()
                        }
                        items(s.data) { ret ->
                            ReturnRow(ret)
                            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReturnRow(ret: ReturnAnalysis) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(ret.drugName, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1.5f), maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(ret.customerName, style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(1.5f), maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text(formatNumber(ret.returnQuantity), style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(0.7f))
        Text(formatCompact(ret.returnAmount), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
        Text("${ret.returnCount}", style = MaterialTheme.typography.bodySmall, modifier = Modifier.weight(0.6f))
    }
}
