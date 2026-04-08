package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Cached gamification leaderboard entry.
 */
@Entity(tableName = "gamification_leaderboard")
data class GamificationLeaderboardEntity(
    @PrimaryKey val staffKey: Int,
    val staffName: String,
    val rank: Int,
    val level: Int,
    val totalXp: Int,
    val currentTier: String,
    val badgeCount: Int,
    val cachedAt: Long = System.currentTimeMillis(),
)

/**
 * Cached badge definition.
 */
@Entity(tableName = "badges_cache")
data class BadgeCacheEntity(
    @PrimaryKey val badgeId: Int,
    val badgeKey: String,
    val titleEn: String,
    val titleAr: String? = null,
    val icon: String,
    val tier: String,
    val category: String,
    val cachedAt: Long = System.currentTimeMillis(),
)
