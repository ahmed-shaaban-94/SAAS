package com.datapulse.android.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "return_cache")
data class ReturnEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val drugName: String,
    val customerName: String,
    val returnQuantity: Double,
    val returnAmount: Double,
    val returnCount: Int,
    val cachedAt: Long,
)
