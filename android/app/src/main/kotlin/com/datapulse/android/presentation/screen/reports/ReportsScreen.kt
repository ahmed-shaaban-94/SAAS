package com.datapulse.android.presentation.screen.reports

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

data class ReportTemplate(
    val id: String,
    val title: String,
    val description: String,
    val category: String,
)

private val reportTemplates = listOf(
    ReportTemplate("daily_sales", "Daily Sales Report", "Revenue, transactions, and KPIs for a selected date", "Sales"),
    ReportTemplate("monthly_summary", "Monthly Summary", "Month-over-month comparison with growth metrics", "Sales"),
    ReportTemplate("product_performance", "Product Performance", "Top products by revenue, quantity, and return rate", "Product"),
    ReportTemplate("customer_analysis", "Customer Analysis", "Customer segmentation and purchase patterns", "Customer"),
    ReportTemplate("staff_leaderboard", "Staff Leaderboard", "Staff performance rankings and commission report", "Staff"),
    ReportTemplate("site_comparison", "Site Comparison", "Side-by-side site metrics comparison", "Site"),
    ReportTemplate("returns_analysis", "Returns Analysis", "Return rates by product and customer", "Returns"),
    ReportTemplate("pipeline_status", "Pipeline Status", "Pipeline run history and quality gate results", "Pipeline"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen() {
    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    "Reports",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        LazyColumn(modifier = Modifier.padding(horizontal = 16.dp)) {
            item {
                Text(
                    "Report Templates",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(vertical = 8.dp),
                )
            }
            items(reportTemplates) { template ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                    ),
                ) {
                    ListItem(
                        headlineContent = {
                            Text(
                                template.title,
                                fontWeight = FontWeight.SemiBold,
                            )
                        },
                        supportingContent = {
                            Text(
                                template.description,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                            )
                        },
                        overlineContent = {
                            Text(
                                template.category,
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary,
                            )
                        },
                        trailingContent = {
                            IconButton(onClick = { /* TODO: generate + share */ }) {
                                Icon(Icons.Default.Share, contentDescription = "Share report")
                            }
                        },
                    )
                }
            }
            item { Spacer(modifier = Modifier.height(16.dp)) }
        }
    }
}
