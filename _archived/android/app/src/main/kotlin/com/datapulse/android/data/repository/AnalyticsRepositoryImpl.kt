package com.datapulse.android.data.repository

import com.datapulse.android.data.local.dao.*
import com.datapulse.android.data.mapper.AnalyticsMapper.toDailyEntities
import com.datapulse.android.data.mapper.AnalyticsMapper.toDailyPoints
import com.datapulse.android.data.mapper.AnalyticsMapper.toDomain
import com.datapulse.android.data.mapper.AnalyticsMapper.toEntities
import com.datapulse.android.data.mapper.AnalyticsMapper.toEntity
import com.datapulse.android.data.mapper.AnalyticsMapper.toMonthlyEntities
import com.datapulse.android.data.mapper.AnalyticsMapper.toMonthlyPoints
import com.datapulse.android.data.mapper.AnalyticsMapper.toRankingResult
import com.datapulse.android.data.remote.ApiService
import com.datapulse.android.domain.model.*
import com.datapulse.android.domain.repository.AnalyticsRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AnalyticsRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val kpiDao: KpiDao,
    private val trendDao: TrendDao,
    private val rankingDao: RankingDao,
    private val returnDao: ReturnDao,
) : AnalyticsRepository {

    override fun getSummary(startDate: String?, endDate: String?, forceRefresh: Boolean): Flow<Resource<KpiSummary>> = flow {
        val cached = kpiDao.getKpi()?.toDomain()
        if (cached != null && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached))

        try {
            val fresh = api.getSummary(startDate, endDate).toDomain()
            kpiDao.insertKpi(fresh.toEntity())
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached != null) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getDailyTrend(startDate: String?, endDate: String?, forceRefresh: Boolean): Flow<Resource<TrendResult>> = flow {
        val cachedPoints = trendDao.getDailyTrends().toDailyPoints()
        val cached = if (cachedPoints.isNotEmpty()) TrendResult(cachedPoints, 0.0, 0.0, 0.0, 0.0, null) else null
        if (cached != null && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached))

        try {
            val fresh = api.getDailyTrend(startDate, endDate).toDomain()
            trendDao.clearDailyTrends()
            trendDao.insertDailyTrends(fresh.points.toDailyEntities())
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached != null) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getMonthlyTrend(startDate: String?, endDate: String?, forceRefresh: Boolean): Flow<Resource<TrendResult>> = flow {
        val cachedPoints = trendDao.getMonthlyTrends().toMonthlyPoints()
        val cached = if (cachedPoints.isNotEmpty()) TrendResult(cachedPoints, 0.0, 0.0, 0.0, 0.0, null) else null
        if (cached != null && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached))

        try {
            val fresh = api.getMonthlyTrend(startDate, endDate).toDomain()
            trendDao.clearMonthlyTrends()
            trendDao.insertMonthlyTrends(fresh.points.toMonthlyEntities())
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached != null) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    private fun getRanking(
        category: String,
        fetcher: suspend () -> RankingResult,
        forceRefresh: Boolean,
    ): Flow<Resource<RankingResult>> = flow {
        val cached = rankingDao.getByCategory(category).toRankingResult()
        if (cached != null && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached))

        try {
            val fresh = fetcher()
            rankingDao.deleteByCategory(category)
            rankingDao.insertAll(fresh.toEntities(category))
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached != null) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getTopProducts(limit: Int, startDate: String?, endDate: String?, forceRefresh: Boolean) =
        getRanking("product", { api.getTopProducts(limit, startDate, endDate).toDomain() }, forceRefresh)

    override fun getTopCustomers(limit: Int, startDate: String?, endDate: String?, forceRefresh: Boolean) =
        getRanking("customer", { api.getTopCustomers(limit, startDate, endDate).toDomain() }, forceRefresh)

    override fun getTopStaff(limit: Int, startDate: String?, endDate: String?, forceRefresh: Boolean) =
        getRanking("staff", { api.getTopStaff(limit, startDate, endDate).toDomain() }, forceRefresh)

    override fun getSites(startDate: String?, endDate: String?, forceRefresh: Boolean) =
        getRanking("site", { api.getSites(startDate, endDate).toDomain() }, forceRefresh)

    override fun getReturns(limit: Int, startDate: String?, endDate: String?, forceRefresh: Boolean): Flow<Resource<List<ReturnAnalysis>>> = flow {
        val cached = returnDao.getReturns().map { it.toDomain() }
        if (cached.isNotEmpty() && !forceRefresh) emit(Resource.Success(cached, fromCache = true))
        else emit(Resource.Loading(cached.ifEmpty { null }))

        try {
            val fresh = api.getReturns(limit, startDate, endDate).map { it.toDomain() }
            returnDao.clear()
            returnDao.insertAll(fresh.map { it.toEntity() })
            emit(Resource.Success(fresh))
        } catch (e: Exception) {
            if (cached.isNotEmpty()) emit(Resource.Error(e.message ?: "Network error", cached))
            else emit(Resource.Error(e.message ?: "Network error"))
        }
    }

    override fun getHealth(): Flow<Resource<HealthStatus>> = flow {
        emit(Resource.Loading())
        try {
            val health = api.getHealth().toDomain()
            emit(Resource.Success(health))
        } catch (e: Exception) {
            emit(Resource.Error(e.message ?: "Unreachable"))
        }
    }
}
