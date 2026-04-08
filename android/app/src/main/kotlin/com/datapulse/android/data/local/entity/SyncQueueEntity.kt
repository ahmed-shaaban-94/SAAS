package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Queued offline actions waiting to be synced to the server.
 * Each entry represents a mutation (pipeline trigger, etc.) made while offline.
 */
@Entity(tableName = "sync_queue")
data class SyncQueueEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val actionType: String,         // e.g. "trigger_pipeline", "mark_read"
    val payload: String,            // JSON payload
    val status: String = "pending", // pending, in_progress, failed, completed
    val retryCount: Int = 0,
    val maxRetries: Int = 5,
    val errorMessage: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val lastAttemptAt: Long? = null,
)
