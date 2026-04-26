package com.datapulse.android.data.local

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.datapulse.android.data.local.dao.KpiDao
import com.datapulse.android.data.local.entity.KpiEntity
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class KpiDaoTest {

    private lateinit var db: DataPulseDatabase
    private lateinit var kpiDao: KpiDao

    @Before
    fun setup() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            DataPulseDatabase::class.java,
        ).allowMainThreadQueries().build()
        kpiDao = db.kpiDao()
    }

    @After
    fun tearDown() { db.close() }

    @Test
    fun insertAndRetrieveKpi() = runTest {
        val entity = KpiEntity(
            todayNet = 1000.0, mtdNet = 50000.0, ytdNet = 500000.0,
            momGrowthPct = 12.5, yoyGrowthPct = -3.2,
            dailyTransactions = 150, dailyCustomers = 42, cachedAt = System.currentTimeMillis(),
        )
        kpiDao.insertKpi(entity)
        val result = kpiDao.getKpi()
        assertNotNull(result)
        assertEquals(1000.0, result!!.todayNet, 0.01)
        assertEquals(150, result.dailyTransactions)
    }

    @Test
    fun clearDeletesAllKpi() = runTest {
        val entity = KpiEntity(
            todayNet = 1000.0, mtdNet = 50000.0, ytdNet = 500000.0,
            momGrowthPct = null, yoyGrowthPct = null,
            dailyTransactions = 0, dailyCustomers = 0, cachedAt = System.currentTimeMillis(),
        )
        kpiDao.insertKpi(entity)
        kpiDao.clear()
        assertNull(kpiDao.getKpi())
    }

    @Test
    fun deleteOlderThanRemovesStaleData() = runTest {
        val old = KpiEntity(
            todayNet = 0.0, mtdNet = 0.0, ytdNet = 0.0,
            momGrowthPct = null, yoyGrowthPct = null,
            dailyTransactions = 0, dailyCustomers = 0, cachedAt = 1000L,
        )
        kpiDao.insertKpi(old)
        kpiDao.deleteOlderThan(2000L)
        assertNull(kpiDao.getKpi())
    }
}
