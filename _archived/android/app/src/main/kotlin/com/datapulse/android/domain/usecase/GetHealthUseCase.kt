package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.HealthStatus
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.AnalyticsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetHealthUseCase @Inject constructor(
    private val repository: AnalyticsRepository,
) {
    operator fun invoke(): Flow<Resource<HealthStatus>> = repository.getHealth()
}
