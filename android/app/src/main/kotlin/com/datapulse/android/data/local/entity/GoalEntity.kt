package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Cached goal/target data for offline display.
 */
@Entity(tableName = "goals_cache")
data class GoalEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val period: String,
    val targetValue: Double,
    val actualValue: Double,
    val variance: Double,
    val achievementPct: Double,
    val cachedAt: Long = System.currentTimeMillis(),
)
