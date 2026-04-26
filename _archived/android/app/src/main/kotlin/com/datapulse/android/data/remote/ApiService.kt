package com.datapulse.android.data.remote

import com.datapulse.android.data.remote.dto.*
import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ApiService @Inject constructor(
    private val client: HttpClient,
) {
    suspend fun getHealth(): HealthStatusDto =
        client.get("/health").body()

    suspend fun getSummary(startDate: String? = null, endDate: String? = null): KpiSummaryDto =
        client.get("/api/v1/analytics/summary") {
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getDailyTrend(startDate: String? = null, endDate: String? = null): TrendResultDto =
        client.get("/api/v1/analytics/trends/daily") {
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getMonthlyTrend(startDate: String? = null, endDate: String? = null): TrendResultDto =
        client.get("/api/v1/analytics/trends/monthly") {
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getTopProducts(limit: Int = 10, startDate: String? = null, endDate: String? = null): RankingResultDto =
        client.get("/api/v1/analytics/products/top") {
            parameter("limit", limit)
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getTopCustomers(limit: Int = 10, startDate: String? = null, endDate: String? = null): RankingResultDto =
        client.get("/api/v1/analytics/customers/top") {
            parameter("limit", limit)
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getTopStaff(limit: Int = 10, startDate: String? = null, endDate: String? = null): RankingResultDto =
        client.get("/api/v1/analytics/staff/top") {
            parameter("limit", limit)
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getSites(startDate: String? = null, endDate: String? = null): RankingResultDto =
        client.get("/api/v1/analytics/sites") {
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getReturns(limit: Int = 20, startDate: String? = null, endDate: String? = null): List<ReturnAnalysisDto> =
        client.get("/api/v1/analytics/returns") {
            parameter("limit", limit)
            startDate?.let { parameter("start_date", it) }
            endDate?.let { parameter("end_date", it) }
        }.body()

    suspend fun getPipelineRuns(page: Int = 1, pageSize: Int = 20): PipelineRunListDto =
        client.get("/api/v1/pipeline/runs") {
            parameter("page", page)
            parameter("page_size", pageSize)
        }.body()

    suspend fun getPipelineRun(id: String): PipelineRunDto =
        client.get("/api/v1/pipeline/runs/$id").body()

    suspend fun getQualityChecks(runId: String): QualityCheckListDto =
        client.get("/api/v1/pipeline/runs/$runId/quality").body()

    suspend fun triggerPipeline(): TriggerResponseDto =
        client.post("/api/v1/pipeline/trigger").body()

    // Reports
    suspend fun getReportTemplates(): List<ReportTemplateDto> =
        client.get("/api/v1/reports").body()

    suspend fun getReportTemplate(templateId: String): ReportTemplateDto =
        client.get("/api/v1/reports/$templateId").body()

    suspend fun renderReport(templateId: String, parameters: Map<String, String>): RenderedReportDto =
        client.post("/api/v1/reports/$templateId/render") {
            io.ktor.client.request.setBody(mapOf("parameters" to parameters))
            io.ktor.http.contentType(io.ktor.http.ContentType.Application.Json)
        }.body()
}
