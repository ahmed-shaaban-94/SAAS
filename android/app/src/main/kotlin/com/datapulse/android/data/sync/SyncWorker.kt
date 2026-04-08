package com.datapulse.android.data.sync

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

/**
 * WorkManager worker that processes the sync queue in the background.
 * Scheduled periodically (every 15 minutes) and on connectivity restore.
 */
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val syncEngine: SyncEngine,
    private val prefetchManager: PrefetchManager,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        return try {
            // 1. Process any queued offline actions
            syncEngine.processQueue()

            // 2. Prefetch fresh data for offline use
            prefetchManager.prefetchAll()

            // 3. Clean up old finished actions
            syncEngine.clearFinished()

            Result.success()
        } catch (e: Exception) {
            if (runAttemptCount < 3) {
                Result.retry()
            } else {
                Result.failure()
            }
        }
    }

    companion object {
        const val WORK_NAME = "datapulse_sync"
        const val ONE_TIME_WORK_NAME = "datapulse_sync_now"
    }
}
