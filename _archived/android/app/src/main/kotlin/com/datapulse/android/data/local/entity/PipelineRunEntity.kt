package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "pipeline_run_cache")
data class PipelineRunEntity(
    @PrimaryKey val id: String,
    val tenantId: Int,
    val runType: String,
    val status: String,
    val triggerSource: String?,
    val startedAt: String,
    val finishedAt: String?,
    val durationSeconds: Double?,
    val rowsLoaded: Int?,
    val errorMessage: String?,
    val metadataJson: String,
    val cachedAt: Long,
)
