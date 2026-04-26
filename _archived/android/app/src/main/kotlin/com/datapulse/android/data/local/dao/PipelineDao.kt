package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.PipelineRunEntity

@Dao
interface PipelineDao {
    @Query("SELECT * FROM pipeline_run_cache ORDER BY startedAt DESC")
    suspend fun getRuns(): List<PipelineRunEntity>

    @Query("SELECT * FROM pipeline_run_cache WHERE id = :id")
    suspend fun getRunById(id: String): PipelineRunEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRuns(runs: List<PipelineRunEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRun(run: PipelineRunEntity)

    @Query("DELETE FROM pipeline_run_cache WHERE cachedAt < :before")
    suspend fun deleteOlderThan(before: Long)

    @Query("DELETE FROM pipeline_run_cache")
    suspend fun clear()
}
