package com.datapulse.android.presentation.screen.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.datapulse.android.data.remote.ApiService
import com.datapulse.android.data.remote.dto.RenderedReportDto
import com.datapulse.android.data.remote.dto.ReportTemplateDto
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ReportsUiState(
    val templates: List<ReportTemplateDto> = emptyList(),
    val isLoadingTemplates: Boolean = true,
    val templatesError: String? = null,
    val selectedTemplate: ReportTemplateDto? = null,
    val parameterValues: Map<String, String> = emptyMap(),
    val renderedReport: RenderedReportDto? = null,
    val isRendering: Boolean = false,
    val renderError: String? = null,
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val api: ApiService,
) : ViewModel() {

    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    init { loadTemplates() }

    fun loadTemplates() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoadingTemplates = true, templatesError = null)
            try {
                val templates = api.getReportTemplates()
                _state.value = _state.value.copy(
                    templates = templates,
                    isLoadingTemplates = false,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isLoadingTemplates = false,
                    templatesError = e.message ?: "Failed to load templates",
                )
            }
        }
    }

    fun selectTemplate(template: ReportTemplateDto) {
        // Pre-fill parameters with defaults
        val defaults = template.parameters.associate { param ->
            param.name to (param.default ?: "")
        }
        _state.value = _state.value.copy(
            selectedTemplate = template,
            parameterValues = defaults,
            renderedReport = null,
            renderError = null,
        )
    }

    fun clearSelection() {
        _state.value = _state.value.copy(
            selectedTemplate = null,
            parameterValues = emptyMap(),
            renderedReport = null,
            renderError = null,
        )
    }

    fun updateParameter(name: String, value: String) {
        _state.value = _state.value.copy(
            parameterValues = _state.value.parameterValues + (name to value),
        )
    }

    fun renderReport() {
        val template = _state.value.selectedTemplate ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(isRendering = true, renderError = null)
            try {
                val result = api.renderReport(template.id, _state.value.parameterValues)
                _state.value = _state.value.copy(
                    renderedReport = result,
                    isRendering = false,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    isRendering = false,
                    renderError = e.message ?: "Failed to render report",
                )
            }
        }
    }
}
