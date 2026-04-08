package com.datapulse.android.data.sync

import com.datapulse.android.data.local.dao.SyncQueueDao
import com.datapulse.android.data.local.entity.SyncQueueEntity
import com.datapulse.android.data.remote.ApiService
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Processes queued offline actions when connectivity is restored.
 * Uses FIFO ordering with exponential backoff on failures.
 */
class SyncEngine(
    private val syncQueueDao: SyncQueueDao,
    private val apiService: ApiService,
    private val networkMonitor: NetworkMonitor,
) {
    enum class SyncStatus { IDLE, SYNCING, ERROR }

    private val _status = MutableStateFlow(SyncStatus.IDLE)
    val status = _status.asStateFlow()

    val pendingCount: Flow<Int> = syncQueueDao.getPendingCount()
    val failedCount: Flow<Int> = syncQueueDao.getFailedCount()

    /**
     * Enqueue an action for later sync.
     */
    suspend fun enqueue(actionType: String, payload: String) {
        syncQueueDao.enqueue(
            SyncQueueEntity(
                actionType = actionType,
                payload = payload,
            )
        )
    }

    /**
     * Process all pending actions in FIFO order.
     * Called when connectivity is restored or on periodic sync.
     */
    suspend fun processQueue() {
        if (!networkMonitor.isCurrentlyOnline()) return

        _status.value = SyncStatus.SYNCING
        try {
            val pending = syncQueueDao.getPendingActions()
            for (action in pending) {
                processAction(action)
            }
            _status.value = SyncStatus.IDLE
        } catch (e: Exception) {
            _status.value = SyncStatus.ERROR
        }
    }

    private suspend fun processAction(action: SyncQueueEntity) {
        syncQueueDao.markInProgress(action.id)

        try {
            executeAction(action)
            syncQueueDao.markCompleted(action.id)
        } catch (e: Exception) {
            val backoffMs = calculateBackoff(action.retryCount)
            syncQueueDao.markFailed(action.id, e.message ?: "Unknown error")
            delay(backoffMs)
        }
    }

    private suspend fun executeAction(action: SyncQueueEntity) {
        when (action.actionType) {
            "trigger_pipeline" -> apiService.triggerPipeline()
            // Add more action types as needed
            else -> throw IllegalArgumentException("Unknown action: ${action.actionType}")
        }
    }

    /**
     * Exponential backoff: 2s, 4s, 8s, 16s, 32s
     */
    private fun calculateBackoff(retryCount: Int): Long {
        val baseMs = 2000L
        return baseMs * (1L shl retryCount.coerceAtMost(4))
    }

    /**
     * Clean up completed and permanently failed actions.
     */
    suspend fun clearFinished() {
        syncQueueDao.clearFinished()
    }
}
