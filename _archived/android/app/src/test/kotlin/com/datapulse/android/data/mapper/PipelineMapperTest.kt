package com.datapulse.android.data.mapper

import com.datapulse.android.data.mapper.PipelineMapper.toDomain
import com.datapulse.android.data.mapper.PipelineMapper.toEntity
import com.datapulse.android.data.remote.dto.PipelineRunDto
import com.datapulse.android.data.remote.dto.QualityCheckDto
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class PipelineMapperTest {

    @Test
    fun `PipelineRunDto toDomain maps all fields`() {
        val dto = PipelineRunDto(
            id = "abc-123", tenantId = 1, runType = "full", status = "success",
            triggerSource = "webhook", startedAt = "2024-01-01T10:00:00Z",
            finishedAt = "2024-01-01T10:02:34Z", durationSeconds = 154.0,
            rowsLoaded = 1134073, errorMessage = null, metadata = mapOf("key" to "value"),
        )
        val domain = dto.toDomain()
        assertEquals("abc-123", domain.id)
        assertEquals("full", domain.runType)
        assertEquals("success", domain.status)
        assertEquals(154.0, domain.durationSeconds)
        assertEquals(1134073, domain.rowsLoaded)
        assertEquals("value", domain.metadata["key"])
    }

    @Test
    fun `PipelineRun roundtrip through entity preserves data`() {
        val dto = PipelineRunDto(
            id = "abc-123", tenantId = 1, runType = "full", status = "success",
            startedAt = "2024-01-01T10:00:00Z", metadata = mapOf("k" to "v"),
        )
        val domain = dto.toDomain()
        val entity = domain.toEntity(cachedAt = 5000L)
        val restored = entity.toDomain()
        assertEquals(domain.id, restored.id)
        assertEquals(domain.runType, restored.runType)
        assertEquals(domain.status, restored.status)
        assertEquals(domain.metadata, restored.metadata)
    }

    @Test
    fun `QualityCheckDto toDomain maps all fields`() {
        val dto = QualityCheckDto(
            id = 1, pipelineRunId = "abc", checkName = "row_count",
            stage = "bronze", passed = true, severity = "critical",
            message = "Row count OK", details = mapOf("count" to "1000"),
            createdAt = "2024-01-01T10:00:00Z",
        )
        val domain = dto.toDomain()
        assertEquals("row_count", domain.checkName)
        assertEquals(true, domain.passed)
        assertEquals("critical", domain.severity)
    }
}
