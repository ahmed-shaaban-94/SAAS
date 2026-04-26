package com.datapulse.android.presentation.util

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class FormattersTest {

    @Test
    fun `formatCompact formats millions`() {
        assertEquals("EGP 1.5M", formatCompact(1_500_000.0))
    }

    @Test
    fun `formatCompact formats billions`() {
        assertEquals("EGP 2.3B", formatCompact(2_300_000_000.0))
    }

    @Test
    fun `formatCompact formats thousands`() {
        assertEquals("EGP 500K", formatCompact(500_000.0))
    }

    @Test
    fun `formatCompact formats small numbers`() {
        assertEquals("EGP 999", formatCompact(999.0))
    }

    @Test
    fun `formatPercent formats correctly`() {
        assertEquals("12.5%", formatPercent(12.5))
        assertEquals("0.0%", formatPercent(0.0))
    }

    @Test
    fun `formatDuration formats minutes and seconds`() {
        assertEquals("2m 34s", formatDuration(154.0))
        assertEquals("0m 30s", formatDuration(30.0))
    }

    @Test
    fun `formatNumber formats with commas`() {
        assertEquals("1,134,073", formatNumber(1134073))
    }
}
