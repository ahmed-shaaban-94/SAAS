package com.datapulse.android.presentation.screen.sqllab

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.presentation.common.EmptyState
import com.datapulse.android.presentation.common.ErrorState
import com.datapulse.android.presentation.common.UiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SqlLabScreen(
    viewModel: SqlLabViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    "SQL Lab",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        Column(
            modifier = Modifier
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            OutlinedTextField(
                value = state.query,
                onValueChange = viewModel::updateQuery,
                modifier = Modifier.fillMaxWidth().height(150.dp),
                label = { Text("SQL Query") },
                textStyle = MaterialTheme.typography.bodyMedium.copy(
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                ),
                placeholder = { Text("SELECT * FROM public_marts.fct_sales LIMIT 10") },
            )

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = viewModel::execute,
                enabled = state.query.isNotBlank() && state.results !is UiState.Loading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.results is UiState.Loading) "Running..." else "Run Query")
            }

            Spacer(modifier = Modifier.height(16.dp))

            when (val results = state.results) {
                is UiState.Loading -> {
                    if (state.query.isNotBlank()) {
                        Text(
                            "Executing query...",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                        )
                    }
                }
                is UiState.Empty -> EmptyState(message = "Enter a query and click Run")
                is UiState.Error -> ErrorState(
                    message = results.message,
                    onRetry = viewModel::execute,
                )
                is UiState.Success -> {
                    Text(
                        "${results.data.rows.size} rows returned",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Card(modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState())) {
                        Column(modifier = Modifier.padding(8.dp)) {
                            // Header row
                            Text(
                                results.data.columns.joinToString(" | "),
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                ),
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            // Data rows
                            results.data.rows.take(100).forEach { row ->
                                Text(
                                    row.joinToString(" | "),
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        fontFamily = FontFamily.Monospace,
                                    ),
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
