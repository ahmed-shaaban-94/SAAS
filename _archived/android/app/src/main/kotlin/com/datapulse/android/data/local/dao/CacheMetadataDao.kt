package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.CacheMetadata

@Dao
interface CacheMetadataDao {
    @Query("SELECT * FROM cache_metadata WHERE cacheKey = :key")
    suspend fun get(key: String): CacheMetadata?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(metadata: CacheMetadata)

    @Query("DELETE FROM cache_metadata WHERE cacheKey = :key")
    suspend fun delete(key: String)

    @Query("DELETE FROM cache_metadata")
    suspend fun clear()

    @Query("SELECT * FROM cache_metadata WHERE lastFetchedAt < :threshold")
    suspend fun getStale(threshold: Long): List<CacheMetadata>

    @Query("DELETE FROM cache_metadata WHERE lastFetchedAt < :threshold")
    suspend fun deleteStale(threshold: Long)
}
