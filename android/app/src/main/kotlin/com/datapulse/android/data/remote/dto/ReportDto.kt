package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ReportTemplateDto(
    val id: String,
    val name: String,
    val description: String = "",
    val parameters: List<ReportParameterDto> = emptyList(),
    val sections: List<ReportSectionDto> = emptyList(),
)

@Serializable
data class ReportParameterDto(
    val name: String,
    val label: String = "",
    @SerialName("param_type") val paramType: String = "text",
    val default: String? = null,
    val options: List<String>? = null,
)

@Serializable
data class ReportSectionDto(
    @SerialName("section_type") val sectionType: String = "text",
    val title: String = "",
    val text: String? = null,
    val sql: String? = null,
    @SerialName("chart_type") val chartType: String? = null,
)

@Serializable
data class RenderedReportDto(
    @SerialName("template_id") val templateId: String,
    @SerialName("template_name") val templateName: String = "",
    val sections: List<RenderedSectionDto> = emptyList(),
)

@Serializable
data class RenderedSectionDto(
    val title: String = "",
    @SerialName("section_type") val sectionType: String = "text",
    val text: String? = null,
    val columns: List<String>? = null,
    val rows: List<List<String?>>? = null,
    val error: String? = null,
)
