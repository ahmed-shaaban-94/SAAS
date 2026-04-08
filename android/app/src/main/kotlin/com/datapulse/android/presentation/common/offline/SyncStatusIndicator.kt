package com.datapulse.android.presentation.common.offline

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material.icons.outlined.CloudSync
import androidx.compose.material.icons.outlined.Warning
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.datapulse.android.data.sync.SyncEngine

/**
 * Small indicator showing sync status (synced/syncing/error).
 * Typically placed in the top bar or settings screen.
 */
@Composable
fun SyncStatusIndicator(
    status: SyncEngine.SyncStatus,
    pendingCount: Int = 0,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        when (status) {
            SyncEngine.SyncStatus.IDLE -> {
                if (pendingCount > 0) {
                    Icon(
                        imageVector = Icons.Outlined.CloudSync,
                        contentDescription = "Pending sync",
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.tertiary,
                    )
                    Text(
                        text = "$pendingCount pending",
                        modifier = Modifier.padding(start = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.tertiary,
                    )
                } else {
                    Icon(
                        imageVector = Icons.Outlined.Check,
                        contentDescription = "Synced",
                        modifier = Modifier.size(16.dp),
                        tint = MaterialTheme.colorScheme.primary,
                    )
                    Text(
                        text = "Synced",
                        modifier = Modifier.padding(start = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }

            SyncEngine.SyncStatus.SYNCING -> {
                Icon(
                    imageVector = Icons.Outlined.CloudSync,
                    contentDescription = "Syncing",
                    modifier = Modifier.size(16.dp),
                    tint = MaterialTheme.colorScheme.secondary,
                )
                Text(
                    text = "Syncing...",
                    modifier = Modifier.padding(start = 4.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.secondary,
                )
            }

            SyncEngine.SyncStatus.ERROR -> {
                Icon(
                    imageVector = Icons.Outlined.Warning,
                    contentDescription = "Sync error",
                    modifier = Modifier.size(16.dp),
                    tint = MaterialTheme.colorScheme.error,
                )
                Text(
                    text = "Sync failed",
                    modifier = Modifier.padding(start = 4.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}
