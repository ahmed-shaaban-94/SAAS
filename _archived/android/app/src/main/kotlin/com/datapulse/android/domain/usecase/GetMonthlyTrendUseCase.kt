package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.model.TrendResult
import com.datapulse.android.domain.repository.AnalyticsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetMonthlyTrendUseCase @Inject constructor(
    private val repository: AnalyticsRepository,
) {
    operator fun invoke(
        startDate: String? = null,
        endDate: String? = null,
        forceRefresh: Boolean = false,
    ): Flow<Resource<TrendResult>> = repository.getMonthlyTrend(startDate, endDate, forceRefresh)
}
