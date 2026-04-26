package com.datapulse.android.domain.repository

import com.datapulse.android.domain.model.*
import kotlinx.coroutines.flow.Flow

interface PipelineRepository {
    fun getRuns(page: Int = 1, pageSize: Int = 20, forceRefresh: Boolean = false): Flow<Resource<List<PipelineRun>>>
    fun getRun(id: String): Flow<Resource<PipelineRun>>
    fun getQualityChecks(runId: String): Flow<Resource<List<QualityCheck>>>
    suspend fun trigger(): Resource<PipelineRun>
}
