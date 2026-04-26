package com.datapulse.android.presentation.common

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun shimmerBrush(): Brush {
    val transition = rememberInfiniteTransition(label = "shimmer")
    val translateAnim by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1000f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "shimmer",
    )
    val shimmerColors = listOf(
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f),
        MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f),
    )
    return Brush.linearGradient(
        colors = shimmerColors,
        start = Offset.Zero,
        end = Offset(x = translateAnim, y = translateAnim),
    )
}

@Composable
fun ShimmerBox(
    modifier: Modifier = Modifier,
    height: Dp = 20.dp,
) {
    Box(
        modifier = modifier
            .height(height)
            .clip(MaterialTheme.shapes.small)
            .background(shimmerBrush()),
    )
}

@Composable
fun KpiCardSkeleton(modifier: Modifier = Modifier) {
    Card(modifier = modifier.padding(4.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.6f), height = 14.dp)
            Spacer(modifier = Modifier.height(8.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.8f), height = 24.dp)
            Spacer(modifier = Modifier.height(4.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.4f), height = 12.dp)
        }
    }
}

@Composable
fun KpiGridSkeleton(modifier: Modifier = Modifier) {
    Column(modifier = modifier.padding(horizontal = 12.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            repeat(3) { KpiCardSkeleton(modifier = Modifier.weight(1f)) }
        }
        Spacer(modifier = Modifier.height(8.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            repeat(3) { KpiCardSkeleton(modifier = Modifier.weight(1f)) }
        }
    }
}

@Composable
fun ChartSkeleton(modifier: Modifier = Modifier) {
    Card(modifier = modifier.padding(horizontal = 12.dp)) {
        Column(modifier = Modifier.padding(16.dp)) {
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.5f), height = 16.dp)
            Spacer(modifier = Modifier.height(16.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth(), height = 200.dp)
        }
    }
}

@Composable
fun ListItemSkeleton(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        ShimmerBox(modifier = Modifier.width(24.dp), height = 20.dp)
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.7f), height = 16.dp)
            Spacer(modifier = Modifier.height(4.dp))
            ShimmerBox(modifier = Modifier.fillMaxWidth(0.4f), height = 12.dp)
        }
    }
}
