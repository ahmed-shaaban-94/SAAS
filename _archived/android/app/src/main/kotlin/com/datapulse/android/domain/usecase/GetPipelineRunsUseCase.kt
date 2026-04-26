package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.PipelineRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetPipelineRunsUseCase @Inject constructor(
    private val repository: PipelineRepository,
) {
    operator fun invoke(
        page: Int = 1,
        pageSize: Int = 20,
        forceRefresh: Boolean = false,
    ): Flow<Resource<List<PipelineRun>>> = repository.getRuns(page, pageSize, forceRefresh)
}
