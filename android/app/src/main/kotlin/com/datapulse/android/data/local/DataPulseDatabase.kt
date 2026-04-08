package com.datapulse.android.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.datapulse.android.data.local.converter.Converters
import com.datapulse.android.data.local.dao.*
import com.datapulse.android.data.local.entity.*

@Database(
    entities = [
        KpiEntity::class,
        DailyTrendEntity::class,
        MonthlyTrendEntity::class,
        RankingEntity::class,
        ReturnEntity::class,
        PipelineRunEntity::class,
        CacheMetadata::class,
        SyncQueueEntity::class,
        GamificationLeaderboardEntity::class,
        BadgeCacheEntity::class,
        GoalEntity::class,
    ],
    version = 2,
    exportSchema = false,
)
@TypeConverters(Converters::class)
abstract class DataPulseDatabase : RoomDatabase() {
    abstract fun kpiDao(): KpiDao
    abstract fun trendDao(): TrendDao
    abstract fun rankingDao(): RankingDao
    abstract fun returnDao(): ReturnDao
    abstract fun pipelineDao(): PipelineDao
    abstract fun cacheMetadataDao(): CacheMetadataDao
    abstract fun syncQueueDao(): SyncQueueDao
    abstract fun gamificationDao(): GamificationDao
    abstract fun goalDao(): GoalDao
}
