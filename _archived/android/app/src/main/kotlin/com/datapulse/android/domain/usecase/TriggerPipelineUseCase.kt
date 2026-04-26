package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.PipelineRepository
import javax.inject.Inject

class TriggerPipelineUseCase @Inject constructor(
    private val repository: PipelineRepository,
) {
    suspend operator fun invoke(): Resource<PipelineRun> = repository.trigger()
}
