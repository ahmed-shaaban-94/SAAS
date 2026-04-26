package com.datapulse.android.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.datapulse.android.data.local.entity.KpiEntity

@Dao
interface KpiDao {
    @Query("SELECT * FROM kpi_cache WHERE id = 1")
    suspend fun getKpi(): KpiEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertKpi(kpi: KpiEntity)

    @Query("DELETE FROM kpi_cache WHERE cachedAt < :before")
    suspend fun deleteOlderThan(before: Long)

    @Query("DELETE FROM kpi_cache")
    suspend fun clear()
}
