package com.datapulse.android.presentation.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

@Immutable
data class DataPulseColors(
    val chartBlue: Color,
    val chartAmber: Color,
    val growthGreen: Color,
    val growthRed: Color,
    val border: Color,
    val divider: Color,
)

val LocalDataPulseColors = staticCompositionLocalOf {
    DataPulseColors(
        chartBlue = ChartBlue,
        chartAmber = ChartAmber,
        growthGreen = GrowthGreen,
        growthRed = GrowthRed,
        border = DarkBorder,
        divider = DarkDivider,
    )
}

private val DarkColorScheme = darkColorScheme(
    background = DarkBackground,
    surface = DarkSurface,
    surfaceVariant = DarkSurfaceVariant,
    surfaceContainer = DarkSurface,
    onBackground = DarkOnBackground,
    onSurface = DarkOnBackground,
    onSurfaceVariant = DarkOnSurfaceVariant,
    primary = DarkAccent,
    onPrimary = DarkBackground,
    secondary = DarkAccentVariant,
    tertiary = ChartBlue,
    outline = DarkBorder,
    outlineVariant = DarkDivider,
)

private val LightColorScheme = lightColorScheme(
    background = LightBackground,
    surface = LightSurface,
    surfaceVariant = LightSurfaceVariant,
    surfaceContainer = LightSurface,
    onBackground = LightOnBackground,
    onSurface = LightOnBackground,
    onSurfaceVariant = LightOnSurfaceVariant,
    primary = LightAccent,
    onPrimary = LightSurface,
    secondary = LightAccentVariant,
    tertiary = ChartBlueDark,
    outline = LightBorder,
    outlineVariant = LightDivider,
)

@Composable
fun DataPulseTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    val dataPulseColors = if (darkTheme) {
        DataPulseColors(
            chartBlue = ChartBlue,
            chartAmber = ChartAmber,
            growthGreen = GrowthGreen,
            growthRed = GrowthRed,
            border = DarkBorder,
            divider = DarkDivider,
        )
    } else {
        DataPulseColors(
            chartBlue = ChartBlueDark,
            chartAmber = ChartAmberDark,
            growthGreen = GrowthGreenDark,
            growthRed = GrowthRedDark,
            border = LightBorder,
            divider = LightDivider,
        )
    }

    CompositionLocalProvider(LocalDataPulseColors provides dataPulseColors) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = DataPulseTypography,
            shapes = DataPulseShapes,
            content = content,
        )
    }
}

object DataPulseThemeExtras {
    val colors: DataPulseColors
        @Composable
        get() = LocalDataPulseColors.current
}
