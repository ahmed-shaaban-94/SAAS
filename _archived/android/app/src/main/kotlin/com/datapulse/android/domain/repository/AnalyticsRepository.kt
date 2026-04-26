package com.datapulse.android.domain.repository

import com.datapulse.android.domain.model.*
import kotlinx.coroutines.flow.Flow

interface AnalyticsRepository {
    fun getSummary(startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<KpiSummary>>
    fun getDailyTrend(startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<TrendResult>>
    fun getMonthlyTrend(startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<TrendResult>>
    fun getTopProducts(limit: Int = 10, startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<RankingResult>>
    fun getTopCustomers(limit: Int = 10, startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<RankingResult>>
    fun getTopStaff(limit: Int = 10, startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<RankingResult>>
    fun getSites(startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<RankingResult>>
    fun getReturns(limit: Int = 20, startDate: String? = null, endDate: String? = null, forceRefresh: Boolean = false): Flow<Resource<List<ReturnAnalysis>>>
    fun getHealth(): Flow<Resource<HealthStatus>>
}
