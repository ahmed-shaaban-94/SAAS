package com.datapulse.android.presentation.util

import java.time.LocalDate
import java.time.format.DateTimeFormatter

data class DatePreset(
    val label: String,
    val startDate: String,
    val endDate: String,
)

fun getDatePresets(): List<DatePreset> {
    val today = LocalDate.now()
    val fmt = DateTimeFormatter.ISO_LOCAL_DATE
    return listOf(
        DatePreset("7D", today.minusDays(7).format(fmt), today.format(fmt)),
        DatePreset("30D", today.minusDays(30).format(fmt), today.format(fmt)),
        DatePreset("90D", today.minusDays(90).format(fmt), today.format(fmt)),
        DatePreset("YTD", today.withDayOfYear(1).format(fmt), today.format(fmt)),
        DatePreset("1Y", today.minusYears(1).format(fmt), today.format(fmt)),
        DatePreset("All", "", ""),
    )
}

fun parsePeriod(period: String): String {
    return try {
        if (period.length == 7) {
            // Monthly: "2024-01" -> "Jan 2024"
            val parts = period.split("-")
            val month = java.time.Month.of(parts[1].toInt()).name.take(3)
                .lowercase().replaceFirstChar { it.uppercase() }
            "$month ${parts[0]}"
        } else {
            // Daily: "2024-01-15" -> "Jan 15"
            val date = LocalDate.parse(period)
            val month = date.month.name.take(3).lowercase().replaceFirstChar { it.uppercase() }
            "$month ${date.dayOfMonth}"
        }
    } catch (_: Exception) {
        period
    }
}

fun formatRelativeTime(isoDateTime: String): String {
    return try {
        val dateTime = java.time.LocalDateTime.parse(isoDateTime.replace("Z", "").substringBefore("+"))
        val now = java.time.LocalDateTime.now()
        val minutes = java.time.Duration.between(dateTime, now).toMinutes()
        when {
            minutes < 1 -> "just now"
            minutes < 60 -> "${minutes}m ago"
            minutes < 1440 -> "${minutes / 60}h ago"
            else -> "${minutes / 1440}d ago"
        }
    } catch (_: Exception) {
        isoDateTime
    }
}
