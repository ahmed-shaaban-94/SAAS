package com.datapulse.android.domain.model

data class ReturnAnalysis(
    val drugName: String,
    val customerName: String,
    val returnQuantity: Double,
    val returnAmount: Double,
    val returnCount: Int,
)
