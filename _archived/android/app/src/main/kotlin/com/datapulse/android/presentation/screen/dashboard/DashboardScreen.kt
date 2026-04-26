package com.datapulse.android.presentation.screen.dashboard

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import com.datapulse.android.presentation.common.ChartMode
import com.datapulse.android.presentation.common.ChartSkeleton
import com.datapulse.android.presentation.common.EmptyState
import com.datapulse.android.presentation.common.ErrorState
import com.datapulse.android.presentation.common.HealthIndicator
import com.datapulse.android.presentation.common.HealthLevel
import com.datapulse.android.presentation.common.KpiCard
import com.datapulse.android.presentation.common.KpiGridSkeleton
import com.datapulse.android.presentation.common.DateFilterBar
import com.datapulse.android.presentation.common.PullRefreshWrapper
import com.datapulse.android.presentation.common.TrendChart
import com.datapulse.android.presentation.common.UiState
import com.datapulse.android.presentation.util.formatCompact
import com.datapulse.android.presentation.util.formatNumber

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    text = "DataPulse",
                    fontWeight = FontWeight.Bold,
                )
            },
            actions = {
                val healthLevel = when {
                    state.health?.isHealthy == true && state.health?.isDegraded == false -> HealthLevel.Healthy
                    state.health?.isDegraded == true -> HealthLevel.Degraded
                    else -> HealthLevel.Down
                }
                HealthIndicator(
                    level = healthLevel,
                    modifier = Modifier.padding(end = 16.dp),
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        PullRefreshWrapper(
            isRefreshing = state.isRefreshing,
            onRefresh = { viewModel.refresh() },
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(bottom = 16.dp),
            ) {
                DateFilterBar(
                    selectedPreset = state.selectedPreset,
                    onPresetSelected = { viewModel.selectPreset(it) },
                )

                when (val kpi = state.kpi) {
                    is UiState.Loading -> KpiGridSkeleton()
                    is UiState.Error -> ErrorState(
                        message = kpi.message,
                        onRetry = { viewModel.refresh() },
                    )
                    is UiState.Empty -> EmptyState()
                    is UiState.Success -> {
                        val data = kpi.data
                        // Row 1: Revenue KPIs
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            KpiCard(
                                title = "Today Net",
                                value = formatCompact(data.todayNet),
                                modifier = Modifier.weight(1f),
                            )
                            KpiCard(
                                title = "MTD Net",
                                value = formatCompact(data.mtdNet),
                                trend = data.momGrowthPct,
                                trendLabel = "MoM",
                                modifier = Modifier.weight(1f),
                            )
                            KpiCard(
                                title = "YTD Net",
                                value = formatCompact(data.ytdNet),
                                trend = data.yoyGrowthPct,
                                trendLabel = "YoY",
                                modifier = Modifier.weight(1f),
                            )
                        }
                        Spacer(modifier = Modifier.height(4.dp))
                        // Row 2: Activity KPIs
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(4.dp),
                        ) {
                            KpiCard(
                                title = "MoM Growth",
                                value = data.momGrowthPct?.let { "${"%.1f".format(it)}%" } ?: "N/A",
                                modifier = Modifier.weight(1f),
                            )
                            KpiCard(
                                title = "Transactions",
                                value = formatNumber(data.dailyTransactions),
                                modifier = Modifier.weight(1f),
                            )
                            KpiCard(
                                title = "Customers",
                                value = formatNumber(data.dailyCustomers),
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Daily Trend Chart
                when (val daily = state.dailyTrend) {
                    is UiState.Loading -> ChartSkeleton()
                    is UiState.Error -> {}
                    is UiState.Empty -> {}
                    is UiState.Success -> TrendChart(
                        title = "Daily Revenue Trend",
                        points = daily.data.points,
                        mode = ChartMode.Line,
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Monthly Trend Chart
                when (val monthly = state.monthlyTrend) {
                    is UiState.Loading -> ChartSkeleton()
                    is UiState.Error -> {}
                    is UiState.Empty -> {}
                    is UiState.Success -> TrendChart(
                        title = "Monthly Revenue",
                        points = monthly.data.points,
                        mode = ChartMode.Bar,
                    )
                }
            }
        }
    }
}
