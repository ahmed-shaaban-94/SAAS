package com.datapulse.android.presentation.util

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class DateUtilsTest {

    @Test
    fun `getDatePresets returns 6 presets`() {
        val presets = getDatePresets()
        assertEquals(6, presets.size)
        assertEquals("7D", presets[0].label)
        assertEquals("All", presets[5].label)
    }

    @Test
    fun `parsePeriod formats monthly period`() {
        val result = parsePeriod("2024-01")
        assertEquals("Jan 2024", result)
    }

    @Test
    fun `parsePeriod formats daily period`() {
        val result = parsePeriod("2024-01-15")
        assertEquals("Jan 15", result)
    }

    @Test
    fun `parsePeriod handles invalid input`() {
        val result = parsePeriod("invalid")
        assertEquals("invalid", result)
    }

    @Test
    fun `All preset has empty dates`() {
        val all = getDatePresets().last()
        assertTrue(all.startDate.isEmpty())
        assertTrue(all.endDate.isEmpty())
    }
}
