package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.DailyTrendEntity
import com.datapulse.android.data.local.entity.MonthlyTrendEntity

@Dao
interface TrendDao {
    @Query("SELECT * FROM daily_trend_cache ORDER BY period ASC")
    suspend fun getDailyTrends(): List<DailyTrendEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertDailyTrends(trends: List<DailyTrendEntity>)

    @Query("DELETE FROM daily_trend_cache")
    suspend fun clearDailyTrends()

    @Query("SELECT * FROM monthly_trend_cache ORDER BY period ASC")
    suspend fun getMonthlyTrends(): List<MonthlyTrendEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMonthlyTrends(trends: List<MonthlyTrendEntity>)

    @Query("DELETE FROM monthly_trend_cache")
    suspend fun clearMonthlyTrends()

    @Query("DELETE FROM daily_trend_cache WHERE cachedAt < :before")
    suspend fun deleteDailyOlderThan(before: Long)

    @Query("DELETE FROM monthly_trend_cache WHERE cachedAt < :before")
    suspend fun deleteMonthlyOlderThan(before: Long)
}
