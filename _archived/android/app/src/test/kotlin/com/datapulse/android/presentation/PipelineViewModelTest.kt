package com.datapulse.android.presentation

import com.datapulse.android.domain.model.PipelineRun
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetPipelineRunsUseCase
import com.datapulse.android.domain.usecase.TriggerPipelineUseCase
import com.datapulse.android.presentation.common.UiState
import com.datapulse.android.presentation.screen.pipeline.PipelineViewModel
import io.mockk.coEvery
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PipelineViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private val getPipelineRuns = mockk<GetPipelineRunsUseCase>()
    private val triggerPipeline = mockk<TriggerPipelineUseCase>()

    private val run = PipelineRun(
        id = "abc", tenantId = 1, runType = "full", status = "success",
        triggerSource = "api", startedAt = "2024-01-01T10:00:00Z",
        finishedAt = "2024-01-01T10:02:34Z", durationSeconds = 154.0,
        rowsLoaded = 1134073, errorMessage = null, metadata = emptyMap(),
    )

    @BeforeEach
    fun setup() { Dispatchers.setMain(testDispatcher) }

    @AfterEach
    fun tearDown() { Dispatchers.resetMain() }

    @Test
    fun `loads runs on init`() = runTest {
        every { getPipelineRuns(any(), any(), any()) } returns flowOf(Resource.Success(listOf(run)))
        val vm = PipelineViewModel(getPipelineRuns, triggerPipeline)
        advanceUntilIdle()
        assertTrue(vm.state.value.runs is UiState.Success)
    }

    @Test
    fun `trigger calls use case and reloads`() = runTest {
        every { getPipelineRuns(any(), any(), any()) } returns flowOf(Resource.Success(listOf(run)))
        coEvery { triggerPipeline() } returns Resource.Success(run)
        val vm = PipelineViewModel(getPipelineRuns, triggerPipeline)
        advanceUntilIdle()
        vm.trigger()
        advanceUntilIdle()
        assertFalse(vm.state.value.isTriggering)
    }

    @Test
    fun `trigger error sets triggerError`() = runTest {
        every { getPipelineRuns(any(), any(), any()) } returns flowOf(Resource.Success(listOf(run)))
        coEvery { triggerPipeline() } returns Resource.Error("Trigger failed")
        val vm = PipelineViewModel(getPipelineRuns, triggerPipeline)
        advanceUntilIdle()
        vm.trigger()
        advanceUntilIdle()
        assertEquals("Trigger failed", vm.state.value.triggerError)
    }
}
