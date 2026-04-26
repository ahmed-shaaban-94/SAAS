package com.datapulse.android.presentation.util

import java.text.NumberFormat
import java.util.Locale

private val egpFormat = NumberFormat.getCurrencyInstance(Locale("en", "EG")).apply {
    maximumFractionDigits = 0
}

private val compactThresholds = listOf(
    1_000_000_000.0 to "B",
    1_000_000.0 to "M",
    1_000.0 to "K",
)

fun formatEgp(value: Double): String = egpFormat.format(value)

fun formatCompact(value: Double): String {
    for ((threshold, suffix) in compactThresholds) {
        if (value >= threshold) {
            val compact = value / threshold
            return if (compact == compact.toLong().toDouble()) {
                "EGP ${compact.toLong()}$suffix"
            } else {
                "EGP ${"%.1f".format(compact)}$suffix"
            }
        }
    }
    return "EGP ${"%.0f".format(value)}"
}

fun formatPercent(value: Double): String = "${"%.1f".format(value)}%"

fun formatDuration(seconds: Double): String {
    val totalSeconds = seconds.toLong()
    val minutes = totalSeconds / 60
    val secs = totalSeconds % 60
    return "${minutes}m ${secs}s"
}

fun formatNumber(value: Int): String =
    NumberFormat.getNumberInstance(Locale.US).format(value)

fun formatNumber(value: Double): String =
    NumberFormat.getNumberInstance(Locale.US).apply {
        maximumFractionDigits = 0
    }.format(value)
