package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Update
import com.datapulse.android.data.local.entity.SyncQueueEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SyncQueueDao {

    @Insert
    suspend fun enqueue(action: SyncQueueEntity): Long

    @Query("SELECT * FROM sync_queue WHERE status = 'pending' ORDER BY createdAt ASC")
    suspend fun getPendingActions(): List<SyncQueueEntity>

    @Query("SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'")
    fun getPendingCount(): Flow<Int>

    @Update
    suspend fun update(action: SyncQueueEntity)

    @Query("UPDATE sync_queue SET status = 'in_progress', lastAttemptAt = :now WHERE id = :id")
    suspend fun markInProgress(id: Long, now: Long = System.currentTimeMillis())

    @Query("UPDATE sync_queue SET status = 'completed' WHERE id = :id")
    suspend fun markCompleted(id: Long)

    @Query("""
        UPDATE sync_queue SET
            status = CASE WHEN retryCount + 1 >= maxRetries THEN 'failed' ELSE 'pending' END,
            retryCount = retryCount + 1,
            errorMessage = :error,
            lastAttemptAt = :now
        WHERE id = :id
    """)
    suspend fun markFailed(id: Long, error: String, now: Long = System.currentTimeMillis())

    @Query("DELETE FROM sync_queue WHERE status IN ('completed', 'failed')")
    suspend fun clearFinished()

    @Query("SELECT COUNT(*) FROM sync_queue WHERE status = 'failed'")
    fun getFailedCount(): Flow<Int>
}
