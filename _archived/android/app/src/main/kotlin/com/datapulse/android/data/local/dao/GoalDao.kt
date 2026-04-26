package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.GoalEntity

@Dao
interface GoalDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(goals: List<GoalEntity>)

    @Query("SELECT * FROM goals_cache ORDER BY period ASC")
    suspend fun getAll(): List<GoalEntity>

    @Query("DELETE FROM goals_cache")
    suspend fun clear()

    @Query("DELETE FROM goals_cache WHERE cachedAt < :before")
    suspend fun deleteOlderThan(before: Long)
}
