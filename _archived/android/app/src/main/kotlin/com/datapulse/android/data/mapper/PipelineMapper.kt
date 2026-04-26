package com.datapulse.android.data.mapper

import com.datapulse.android.data.local.entity.PipelineRunEntity
import com.datapulse.android.data.remote.dto.PipelineRunDto
import com.datapulse.android.data.remote.dto.QualityCheckDto
import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.QualityCheck
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

object PipelineMapper {
    private val json = Json { ignoreUnknownKeys = true }

    fun PipelineRunDto.toDomain() = PipelineRun(
        id = id,
        tenantId = tenantId,
        runType = runType,
        status = status,
        triggerSource = triggerSource,
        startedAt = startedAt,
        finishedAt = finishedAt,
        durationSeconds = durationSeconds,
        rowsLoaded = rowsLoaded,
        errorMessage = errorMessage,
        metadata = metadata,
    )

    fun PipelineRun.toEntity(cachedAt: Long = System.currentTimeMillis()) = PipelineRunEntity(
        id = id,
        tenantId = tenantId,
        runType = runType,
        status = status,
        triggerSource = triggerSource,
        startedAt = startedAt,
        finishedAt = finishedAt,
        durationSeconds = durationSeconds,
        rowsLoaded = rowsLoaded,
        errorMessage = errorMessage,
        metadataJson = json.encodeToString(metadata),
        cachedAt = cachedAt,
    )

    fun PipelineRunEntity.toDomain() = PipelineRun(
        id = id,
        tenantId = tenantId,
        runType = runType,
        status = status,
        triggerSource = triggerSource,
        startedAt = startedAt,
        finishedAt = finishedAt,
        durationSeconds = durationSeconds,
        rowsLoaded = rowsLoaded,
        errorMessage = errorMessage,
        metadata = try { json.decodeFromString(metadataJson) } catch (_: Exception) { emptyMap() },
    )

    fun QualityCheckDto.toDomain() = QualityCheck(
        id = id,
        pipelineRunId = pipelineRunId,
        checkName = checkName,
        stage = stage,
        passed = passed,
        severity = severity,
        message = message,
        details = details,
        createdAt = createdAt,
    )
}
