package com.datapulse.android.data.repository

import com.datapulse.android.data.local.dao.PipelineDao
import com.datapulse.android.data.mapper.PipelineMapper.toDomain
import com.datapulse.android.data.mapper.PipelineMapper.toEntity
import com.datapulse.android.data.remote.ApiService
import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.QualityCheck
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.PipelineRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PipelineRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val pipelineDao: PipelineDao,
) : PipelineRepository {

    override fun getRuns(page: Int, pageSize: Int, forceRefresh: Boolean): Flow<Resource<List<PipelineRun>>> = flow {
        val cached = pipelineDao.getRuns().map { it.toDomain() }
        if (cached.isNotEmpty() && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached.ifEmpty { null }))

        try {
            val fresh = api.getPipelineRuns(page, pageSize).items.map { it.toDomain() }
            pipelineDao.clear()
            pipelineDao.insertRuns(fresh.map { it.toEntity() })
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached.isNotEmpty()) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getRun(id: String): Flow<Resource<PipelineRun>> = flow {
        val cached = pipelineDao.getRunById(id)?.toDomain()
        if (cached != null) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading())

        try {
            val fresh = api.getPipelineRun(id).toDomain()
            pipelineDao.insertRun(fresh.toEntity())
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached != null) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getQualityChecks(runId: String): Flow<Resource<List<QualityCheck>>> = flow {
        emit(Resource.Loading())
        try {
            val checks = api.getQualityChecks(runId).checks.map { it.toDomain() }
            emit(Resource.Success(checks))
        } catch (e: Exception) {
            emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override suspend fun trigger(): Resource<PipelineRun> = try {
        val response = api.triggerPipeline()
        val run = api.getPipelineRun(response.runId).toDomain()
        pipelineDao.insertRun(run.toEntity())
        Resource.Success(run)
    } catch (e: Exception) {
        Resource.Error(e.message ?: "Trigger failed")
    }
}
