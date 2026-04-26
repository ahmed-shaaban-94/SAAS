package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.QualityCheck
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.PipelineRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetQualityChecksUseCase @Inject constructor(
    private val repository: PipelineRepository,
) {
    operator fun invoke(runId: String): Flow<Resource<List<QualityCheck>>> =
        repository.getQualityChecks(runId)
}
