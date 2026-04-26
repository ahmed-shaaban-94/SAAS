package com.datapulse.android.presentation

import com.datapulse.android.domain.model.RankingItem
import com.datapulse.android.domain.model.RankingResult
import com.datapulse.android.domain.model.Resource
import com.datapulse.android.domain.usecase.GetTopProductsUseCase
import com.datapulse.android.presentation.common.UiState
import com.datapulse.android.presentation.screen.products.ProductsViewModel
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
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProductsViewModelTest {

    private val testDispatcher = StandardTestDispatcher()
    private val getTopProducts = mockk<GetTopProductsUseCase>()

    @BeforeEach
    fun setup() { Dispatchers.setMain(testDispatcher) }

    @AfterEach
    fun tearDown() { Dispatchers.resetMain() }

    @Test
    fun `loads products on init`() = runTest {
        val ranking = RankingResult(
            listOf(RankingItem(1, 10, "Drug A", 5000.0, 50.0)),
            10000.0,
        )
        every { getTopProducts(any(), any(), any(), any()) } returns flowOf(Resource.Success(ranking))
        val vm = ProductsViewModel(getTopProducts)
        advanceUntilIdle()
        assertTrue(vm.state.value is UiState.Success)
        assertEquals(1, (vm.state.value as UiState.Success).data.items.size)
    }

    @Test
    fun `empty result shows empty state`() = runTest {
        every { getTopProducts(any(), any(), any(), any()) } returns flowOf(Resource.Success(RankingResult(emptyList(), 0.0)))
        val vm = ProductsViewModel(getTopProducts)
        advanceUntilIdle()
        assertTrue(vm.state.value is UiState.Empty)
    }
}
