package com.datapulse.android.presentation.screen.reports

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.datapulse.android.data.remote.dto.RenderedSectionDto
import com.datapulse.android.data.remote.dto.ReportParameterDto
import com.datapulse.android.data.remote.dto.ReportTemplateDto
import com.datapulse.android.presentation.common.ErrorState
import com.datapulse.android.presentation.common.LoadingSkeleton

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportsScreen(
    viewModel: ReportsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Column(modifier = Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Text(
                    if (state.selectedTemplate != null) state.selectedTemplate!!.name else "Reports",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            },
            navigationIcon = {
                if (state.selectedTemplate != null) {
                    IconButton(onClick = { viewModel.clearSelection() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
            ),
        )

        if (state.selectedTemplate != null) {
            ReportDetailView(
                template = state.selectedTemplate!!,
                parameterValues = state.parameterValues,
                onParameterChange = viewModel::updateParameter,
                onRender = viewModel::renderReport,
                isRendering = state.isRendering,
                renderedReport = state.renderedReport,
                renderError = state.renderError,
            )
        } else {
            TemplateListView(
                templates = state.templates,
                isLoading = state.isLoadingTemplates,
                error = state.templatesError,
                onSelect = viewModel::selectTemplate,
                onRetry = viewModel::loadTemplates,
            )
        }
    }
}

@Composable
private fun TemplateListView(
    templates: List<ReportTemplateDto>,
    isLoading: Boolean,
    error: String?,
    onSelect: (ReportTemplateDto) -> Unit,
    onRetry: () -> Unit,
) {
    when {
        isLoading -> {
            Column(modifier = Modifier.padding(16.dp)) {
                repeat(4) {
                    LoadingSkeleton.ListItemSkeleton()
                    Spacer(Modifier.height(8.dp))
                }
            }
        }
        error != null -> {
            ErrorState(message = error, onRetry = onRetry)
        }
        templates.isEmpty() -> {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No report templates available", color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
            }
        }
        else -> {
            LazyColumn(modifier = Modifier.padding(horizontal = 16.dp)) {
                item { Spacer(Modifier.height(8.dp)) }
                items(templates) { template ->
                    TemplateCard(template = template, onClick = { onSelect(template) })
                    Spacer(Modifier.height(8.dp))
                }
                item { Spacer(Modifier.height(16.dp)) }
            }
        }
    }
}

@Composable
private fun TemplateCard(
    template: ReportTemplateDto,
    onClick: () -> Unit,
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                template.name,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            if (template.description.isNotBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    template.description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f),
                )
            }
            if (template.parameters.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text(
                    "${template.parameters.size} parameter(s)",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun ReportDetailView(
    template: ReportTemplateDto,
    parameterValues: Map<String, String>,
    onParameterChange: (String, String) -> Unit,
    onRender: () -> Unit,
    isRendering: Boolean,
    renderedReport: com.datapulse.android.data.remote.dto.RenderedReportDto?,
    renderError: String?,
) {
    LazyColumn(modifier = Modifier.padding(horizontal = 16.dp)) {
        // Parameters
        if (template.parameters.isNotEmpty()) {
            item {
                Text(
                    "Parameters",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(vertical = 8.dp),
                )
            }
            items(template.parameters) { param ->
                ParameterField(
                    param = param,
                    value = parameterValues[param.name] ?: "",
                    onValueChange = { onParameterChange(param.name, it) },
                )
                Spacer(Modifier.height(8.dp))
            }
        }

        // Generate button
        item {
            Spacer(Modifier.height(8.dp))
            Button(
                onClick = onRender,
                enabled = !isRendering,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (isRendering) {
                    CircularProgressIndicator(
                        modifier = Modifier.height(20.dp).width(20.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("Generating...")
                } else {
                    Icon(Icons.Default.PlayArrow, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Generate Report")
                }
            }
            Spacer(Modifier.height(16.dp))
        }

        // Error
        if (renderError != null) {
            item {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.errorContainer,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        renderError,
                        modifier = Modifier.padding(16.dp),
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Spacer(Modifier.height(16.dp))
            }
        }

        // Rendered report
        if (renderedReport != null) {
            item {
                HorizontalDivider(modifier = Modifier.padding(vertical = 8.dp))
                Text(
                    renderedReport.templateName.ifBlank { "Report Results" },
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(vertical = 8.dp),
                )
            }
            items(renderedReport.sections) { section ->
                RenderedSectionView(section)
                Spacer(Modifier.height(12.dp))
            }
            item { Spacer(Modifier.height(32.dp)) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ParameterField(
    param: ReportParameterDto,
    value: String,
    onValueChange: (String) -> Unit,
) {
    if (param.options != null && param.options.isNotEmpty()) {
        // Dropdown
        var expanded by remember { mutableStateOf(false) }
        ExposedDropdownMenuBox(
            expanded = expanded,
            onExpandedChange = { expanded = it },
        ) {
            OutlinedTextField(
                value = value,
                onValueChange = {},
                readOnly = true,
                label = { Text(param.label.ifBlank { param.name }) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
            )
            ExposedDropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false },
            ) {
                param.options.forEach { option ->
                    DropdownMenuItem(
                        text = { Text(option) },
                        onClick = {
                            onValueChange(option)
                            expanded = false
                        },
                    )
                }
            }
        }
    } else {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            label = { Text(param.label.ifBlank { param.name }) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
    }
}

@Composable
private fun RenderedSectionView(section: RenderedSectionDto) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f),
        ),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            if (section.title.isNotBlank()) {
                Text(
                    section.title,
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold,
                )
                Spacer(Modifier.height(8.dp))
            }

            if (section.error != null) {
                Text(
                    section.error,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall,
                )
            } else if (section.sectionType == "text" && section.text != null) {
                Text(
                    section.text,
                    style = MaterialTheme.typography.bodyMedium,
                )
            } else if (section.columns != null && section.rows != null) {
                // Table
                val scrollState = rememberScrollState()
                Row(modifier = Modifier.horizontalScroll(scrollState)) {
                    Column {
                        // Header
                        Row(
                            modifier = Modifier.padding(bottom = 4.dp),
                        ) {
                            section.columns.forEach { col ->
                                Text(
                                    col,
                                    modifier = Modifier.width(120.dp).padding(4.dp),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                        HorizontalDivider()
                        // Rows
                        section.rows.take(50).forEachIndexed { idx, row ->
                            Row(
                                modifier = Modifier.padding(vertical = 2.dp),
                            ) {
                                row.forEachIndexed { colIdx, cell ->
                                    Text(
                                        cell ?: "—",
                                        modifier = Modifier.width(120.dp).padding(4.dp),
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        textAlign = if (colIdx > 0) TextAlign.End else TextAlign.Start,
                                    )
                                }
                            }
                            if (idx < section.rows.size - 1) {
                                HorizontalDivider(
                                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                                )
                            }
                        }
                        if (section.rows.size > 50) {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "Showing 50 of ${section.rows.size} rows",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f),
                            )
                        }
                    }
                }
            }
        }
    }
}
