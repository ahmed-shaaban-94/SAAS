package com.datapulse.android.presentation.common.offline

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import java.util.concurrent.TimeUnit

/**
 * Shows "Last updated: X minutes ago" based on a timestamp.
 */
@Composable
fun LastSyncedLabel(
    lastSyncedAt: Long?,
    modifier: Modifier = Modifier,
) {
    val text = if (lastSyncedAt == null || lastSyncedAt == 0L) {
        "Never synced"
    } else {
        val elapsed = System.currentTimeMillis() - lastSyncedAt
        when {
            elapsed < TimeUnit.MINUTES.toMillis(1) -> "Updated just now"
            elapsed < TimeUnit.HOURS.toMillis(1) -> {
                val minutes = TimeUnit.MILLISECONDS.toMinutes(elapsed)
                "Updated ${minutes}m ago"
            }
            elapsed < TimeUnit.DAYS.toMillis(1) -> {
                val hours = TimeUnit.MILLISECONDS.toHours(elapsed)
                "Updated ${hours}h ago"
            }
            else -> {
                val days = TimeUnit.MILLISECONDS.toDays(elapsed)
                "Updated ${days}d ago"
            }
        }
    }

    Text(
        text = text,
        modifier = modifier,
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}
