package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "cache_metadata")
data class CacheMetadata(
    @PrimaryKey val cacheKey: String,
    val lastFetchedAt: Long,
    val etag: String? = null,
)
