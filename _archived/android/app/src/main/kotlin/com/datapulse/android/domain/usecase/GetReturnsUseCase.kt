package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.ReturnAnalysis
import com.datapulse.android.domain.repository.AnalyticsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetReturnsUseCase @Inject constructor(
    private val repository: AnalyticsRepository,
) {
    operator fun invoke(
        limit: Int = 20,
        startDate: String? = null,
        endDate: String? = null,
        forceRefresh: Boolean = false,
    ): Flow<Resource<List<ReturnAnalysis>>> = repository.getReturns(limit, startDate, endDate, forceRefresh)
}
