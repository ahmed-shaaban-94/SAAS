package com.datapulse.android.presentation.screen.customers

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import com.datapulse.android.presentation.common.*
import com.datapulse.android.presentation.util.formatCompact

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomersScreen(viewModel: CustomersViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val isRefreshing by viewModel.isRefreshing.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Customers", fontWeight = FontWeight.Bold) },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
        )
        PullRefreshWrapper(isRefreshing = isRefreshing, onRefresh = { viewModel.refresh() }) {
            when (val s = state) {
                is UiState.Loading -> Column { KpiGridSkeleton(); Spacer(Modifier.height(16.dp)); ChartSkeleton() }
                is UiState.Error -> ErrorState(message = s.message, onRetry = { viewModel.refresh() })
                is UiState.Empty -> EmptyState()
                is UiState.Success -> {
                    Column(modifier = Modifier.fillMaxSize()) {
                        Text(
                            text = "Total Revenue: ${formatCompact(s.data.total)}",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                        )
                        TrendChart(
                            title = "Top Customers",
                            points = s.data.items.take(10).map {
                                com.datapulse.android.domain.model.TimeSeriesPoint(it.name.take(12), it.value)
                            },
                            mode = ChartMode.Bar,
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        RankingList(items = s.data.items, modifier = Modifier.weight(1f))
                    }
                }
            }
        }
    }
}
