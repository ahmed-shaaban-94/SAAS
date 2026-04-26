package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.ReturnEntity

@Dao
interface ReturnDao {
    @Query("SELECT * FROM return_cache ORDER BY returnAmount DESC")
    suspend fun getReturns(): List<ReturnEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(returns: List<ReturnEntity>)

    @Query("DELETE FROM return_cache")
    suspend fun clear()

    @Query("DELETE FROM return_cache WHERE cachedAt < :before")
    suspend fun deleteOlderThan(before: Long)
}
