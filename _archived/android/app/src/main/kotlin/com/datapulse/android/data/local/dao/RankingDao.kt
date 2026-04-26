package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.RankingEntity

@Dao
interface RankingDao {
    @Query("SELECT * FROM ranking_cache WHERE category = :category ORDER BY rank ASC")
    suspend fun getByCategory(category: String): List<RankingEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(rankings: List<RankingEntity>)

    @Query("DELETE FROM ranking_cache WHERE category = :category")
    suspend fun deleteByCategory(category: String)

    @Query("DELETE FROM ranking_cache WHERE cachedAt < :before")
    suspend fun deleteOlderThan(before: Long)

    @Query("DELETE FROM ranking_cache")
    suspend fun clear()
}
