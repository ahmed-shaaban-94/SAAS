package com.datapulse.android.data.sync

import com.datapulse.android.data.local.dao.CacheMetadataDao
import com.datapulse.android.data.local.entity.CacheMetadata
import com.datapulse.android.data.repository.AnalyticsRepositoryImpl

/**
 * Prefetches critical data for offline use when the device is online.
 *
 * Priority-ordered prefetch:
 * 1. KPI Summary (high priority — dashboard)
 * 2. Daily/Monthly Trends (high — charts)
 * 3. Rankings (medium — leaderboards)
 * 4. Goals/Targets (medium)
 * 5. Pipeline runs (low)
 */
class PrefetchManager(
    private val analyticsRepo: AnalyticsRepositoryImpl,
    private val cacheMetadataDao: CacheMetadataDao,
    private val networkMonitor: NetworkMonitor,
) {
    companion object {
        /** Cache TTL in milliseconds — 15 minutes */
        const val CACHE_TTL_MS = 15 * 60 * 1000L
    }

    /**
     * Prefetch all critical data if cache is stale.
     */
    suspend fun prefetchAll() {
        if (!networkMonitor.isCurrentlyOnline()) return

        prefetchIfStale("kpi_summary") {
            analyticsRepo.getSummary(forceRefresh = true)
        }
        prefetchIfStale("daily_trend") {
            analyticsRepo.getDailyTrend(forceRefresh = true)
        }
        prefetchIfStale("monthly_trend") {
            analyticsRepo.getMonthlyTrend(forceRefresh = true)
        }
        prefetchIfStale("top_products") {
            analyticsRepo.getTopProducts(forceRefresh = true)
        }
        prefetchIfStale("top_customers") {
            analyticsRepo.getTopCustomers(forceRefresh = true)
        }
        prefetchIfStale("top_staff") {
            analyticsRepo.getTopStaff(forceRefresh = true)
        }
    }

    private suspend fun prefetchIfStale(key: String, fetch: suspend () -> Any) {
        val metadata = cacheMetadataDao.get(key)
        val isStale = metadata == null ||
            (System.currentTimeMillis() - metadata.lastFetchedAt) > CACHE_TTL_MS

        if (isStale) {
            try {
                fetch()
                cacheMetadataDao.upsert(
                    CacheMetadata(
                        cacheKey = key,
                        lastFetchedAt = System.currentTimeMillis(),
                    )
                )
            } catch (_: Exception) {
                // Prefetch failures are non-critical; skip silently
            }
        }
    }
}
