package com.datapulse.android.domain.usecase

import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.repository.PipelineRepository
import io.mockk.coEvery
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class TriggerPipelineUseCaseTest {

    private val repository = mockk<PipelineRepository>()
    private val useCase = TriggerPipelineUseCase(repository)

    private val run = PipelineRun(
        id = "abc", tenantId = 1, runType = "full", status = "running",
        triggerSource = "api", startedAt = "2024-01-01T10:00:00Z",
        finishedAt = null, durationSeconds = null, rowsLoaded = null,
        errorMessage = null, metadata = emptyMap(),
    )

    @Test
    fun `invoke returns success when trigger succeeds`() = runTest {
        coEvery { repository.trigger() } returns Resource.Success(run)
        val result = useCase()
        assertTrue(result is Resource.Success)
        assertEquals("abc", (result as Resource.Success).data.id)
    }

    @Test
    fun `invoke returns error when trigger fails`() = runTest {
        coEvery { repository.trigger() } returns Resource.Error("Trigger failed")
        val result = useCase()
        assertTrue(result is Resource.Error)
        assertEquals("Trigger failed", (result as Resource.Error).message)
    }
}
