package com.datapulse.android.presentation.common

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import com.datapulse.android.presentation.theme.DataPulseThemeExtras

enum class HealthLevel { Healthy, Degraded, Down }

@Composable
fun HealthIndicator(
    level: HealthLevel,
    modifier: Modifier = Modifier,
) {
    val extras = DataPulseThemeExtras.colors
    val color = when (level) {
        HealthLevel.Healthy -> extras.growthGreen
        HealthLevel.Degraded -> extras.chartAmber
        HealthLevel.Down -> extras.growthRed
    }
    Box(
        modifier = modifier
            .size(10.dp)
            .clip(CircleShape)
            .background(color),
    )
}
