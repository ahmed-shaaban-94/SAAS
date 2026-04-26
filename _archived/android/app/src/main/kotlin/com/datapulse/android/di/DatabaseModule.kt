package com.datapulse.android.di

import android.content.Context
import androidx.room.Room
import com.datapulse.android.data.local.DataPulseDatabase
import com.datapulse.android.data.local.dao.*
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): DataPulseDatabase =
        Room.databaseBuilder(context, DataPulseDatabase::class.java, "datapulse.db")
            .fallbackToDestructiveMigration()
            .build()

    @Provides fun provideKpiDao(db: DataPulseDatabase): KpiDao = db.kpiDao()
    @Provides fun provideTrendDao(db: DataPulseDatabase): TrendDao = db.trendDao()
    @Provides fun provideRankingDao(db: DataPulseDatabase): RankingDao = db.rankingDao()
    @Provides fun provideReturnDao(db: DataPulseDatabase): ReturnDao = db.returnDao()
    @Provides fun providePipelineDao(db: DataPulseDatabase): PipelineDao = db.pipelineDao()
    @Provides fun provideCacheMetadataDao(db: DataPulseDatabase): CacheMetadataDao = db.cacheMetadataDao()
}
