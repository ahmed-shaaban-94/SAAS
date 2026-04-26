package com.datapulse.android.presentation.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.datapulse.android.presentation.theme.DataPulseThemeExtras

@Composable
fun StatusBadge(
    status: String,
    modifier: Modifier = Modifier,
) {
    val extras = DataPulseThemeExtras.colors
    val (bgColor, dotColor, label) = when (status.lowercase()) {
        "success", "completed" -> Triple(
            extras.growthGreen.copy(alpha = 0.15f),
            extras.growthGreen,
            "Success",
        )
        "failed", "error" -> Triple(
            extras.growthRed.copy(alpha = 0.15f),
            extras.growthRed,
            "Failed",
        )
        "running", "in_progress" -> Triple(
            extras.chartAmber.copy(alpha = 0.15f),
            extras.chartAmber,
            "Running",
        )
        else -> Triple(
            MaterialTheme.colorScheme.surfaceVariant,
            MaterialTheme.colorScheme.onSurfaceVariant,
            status.replaceFirstChar { it.uppercase() },
        )
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(bgColor)
            .padding(horizontal = 10.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(dotColor),
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = dotColor,
        )
    }
}
