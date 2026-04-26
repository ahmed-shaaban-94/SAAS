package com.datapulse.android.data.local

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.datapulse.android.data.local.dao.PipelineDao
import com.datapulse.android.data.local.entity.PipelineRunEntity
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PipelineDaoTest {

    private lateinit var db: DataPulseDatabase
    private lateinit var dao: PipelineDao

    @Before
    fun setup() {
        db = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            DataPulseDatabase::class.java,
        ).allowMainThreadQueries().build()
        dao = db.pipelineDao()
    }

    @After
    fun tearDown() { db.close() }

    @Test
    fun insertAndRetrieveRuns() = runTest {
        val run = PipelineRunEntity(
            id = "abc-123", tenantId = 1, runType = "full", status = "success",
            triggerSource = "webhook", startedAt = "2024-01-01T10:00:00Z",
            finishedAt = "2024-01-01T10:02:34Z", durationSeconds = 154.0,
            rowsLoaded = 1134073, errorMessage = null, metadataJson = "{}",
            cachedAt = System.currentTimeMillis(),
        )
        dao.insertRuns(listOf(run))
        val results = dao.getRuns()
        assertEquals(1, results.size)
        assertEquals("abc-123", results[0].id)
    }

    @Test
    fun getRunByIdReturnsCorrectRun() = runTest {
        val run = PipelineRunEntity(
            id = "test-id", tenantId = 1, runType = "full", status = "running",
            triggerSource = null, startedAt = "2024-01-01", finishedAt = null,
            durationSeconds = null, rowsLoaded = null, errorMessage = null,
            metadataJson = "{}", cachedAt = System.currentTimeMillis(),
        )
        dao.insertRun(run)
        val result = dao.getRunById("test-id")
        assertNotNull(result)
        assertEquals("running", result!!.status)
    }

    @Test
    fun clearRemovesAllRuns() = runTest {
        val run = PipelineRunEntity(
            id = "x", tenantId = 1, runType = "full", status = "success",
            triggerSource = null, startedAt = "", finishedAt = null,
            durationSeconds = null, rowsLoaded = null, errorMessage = null,
            metadataJson = "{}", cachedAt = 1000L,
        )
        dao.insertRuns(listOf(run))
        dao.clear()
        assertEquals(0, dao.getRuns().size)
    }
}
