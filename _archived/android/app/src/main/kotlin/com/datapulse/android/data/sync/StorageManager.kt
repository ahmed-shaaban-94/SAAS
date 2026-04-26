package com.datapulse.android.data.sync

import com.datapulse.android.data.local.dao.CacheMetadataDao
import com.datapulse.android.data.local.dao.GamificationDao
import com.datapulse.android.data.local.dao.GoalDao
import com.datapulse.android.data.local.dao.KpiDao
import com.datapulse.android.data.local.dao.PipelineDao
import com.datapulse.android.data.local.dao.RankingDao
import com.datapulse.android.data.local.dao.ReturnDao
import com.datapulse.android.data.local.dao.SyncQueueDao
import com.datapulse.android.data.local.dao.TrendDao

/**
 * Manages local storage: clearing caches, removing stale data,
 * and reporting storage statistics.
 */
class StorageManager(
    private val kpiDao: KpiDao,
    private val trendDao: TrendDao,
    private val rankingDao: RankingDao,
    private val returnDao: ReturnDao,
    private val pipelineDao: PipelineDao,
    private val gamificationDao: GamificationDao,
    private val goalDao: GoalDao,
    private val syncQueueDao: SyncQueueDao,
    private val cacheMetadataDao: CacheMetadataDao,
) {
    data class StorageStats(
        val pendingSyncActions: Int,
        val failedSyncActions: Int,
        val cacheEntries: Int,
    )

    /**
     * Clear all cached data (does not affect sync queue).
     */
    suspend fun clearAllCaches() {
        kpiDao.clear()
        trendDao.clearDaily()
        trendDao.clearMonthly()
        rankingDao.clear()
        returnDao.clear()
        pipelineDao.clear()
        gamificationDao.clearLeaderboard()
        gamificationDao.clearBadges()
        goalDao.clear()
        cacheMetadataDao.clearAll()
    }

    /**
     * Remove cached data older than the specified duration.
     */
    suspend fun clearStaleData(maxAgeMs: Long) {
        val before = System.currentTimeMillis() - maxAgeMs
        kpiDao.deleteOlderThan(before)
        trendDao.deleteDailyOlderThan(before)
        trendDao.deleteMonthlyOlderThan(before)
        rankingDao.deleteOlderThan(before)
        returnDao.deleteOlderThan(before)
        pipelineDao.deleteOlderThan(before)
        gamificationDao.deleteLeaderboardOlderThan(before)
        gamificationDao.deleteBadgesOlderThan(before)
        goalDao.deleteOlderThan(before)
    }

    /**
     * Get storage statistics for display in Settings.
     */
    suspend fun getStats(): StorageStats {
        val pending = syncQueueDao.getPendingActions().size
        // Simple count — in a real app, query count(*) directly
        return StorageStats(
            pendingSyncActions = pending,
            failedSyncActions = 0,
            cacheEntries = 0,
        )
    }
}
