package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.BadgeCacheEntity
import com.datapulse.android.data.local.entity.GamificationLeaderboardEntity

@Dao
interface GamificationDao {

    // Leaderboard
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertLeaderboard(entries: List<GamificationLeaderboardEntity>)

    @Query("SELECT * FROM gamification_leaderboard ORDER BY rank ASC")
    suspend fun getLeaderboard(): List<GamificationLeaderboardEntity>

    @Query("DELETE FROM gamification_leaderboard")
    suspend fun clearLeaderboard()

    // Badges
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertBadges(badges: List<BadgeCacheEntity>)

    @Query("SELECT * FROM badges_cache ORDER BY tier, category")
    suspend fun getBadges(): List<BadgeCacheEntity>

    @Query("DELETE FROM badges_cache")
    suspend fun clearBadges()

    @Query("DELETE FROM gamification_leaderboard WHERE cachedAt < :before")
    suspend fun deleteLeaderboardOlderThan(before: Long)

    @Query("DELETE FROM badges_cache WHERE cachedAt < :before")
    suspend fun deleteBadgesOlderThan(before: Long)
}
