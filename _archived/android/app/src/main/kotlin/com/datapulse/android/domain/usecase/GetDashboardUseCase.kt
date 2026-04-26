package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.KpiSummary
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.AnalyticsRepository
import kotlinx.coroutines.flow.Flow
import javax.inject.Inject

class GetDashboardUseCase @Inject constructor(
    private val repository: AnalyticsRepository,
) {
    operator fun invoke(
        startDate: String? = null,
        endDate: String? = null,
        forceRefresh: Boolean = false,
    ): Flow<Resource<KpiSummary>> = repository.getSummary(startDate, endDate, forceRefresh)
}
