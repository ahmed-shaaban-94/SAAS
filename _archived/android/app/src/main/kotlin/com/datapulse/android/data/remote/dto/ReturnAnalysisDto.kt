package com.datapulse.android.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ReturnAnalysisDto(
    @SerialName("drug_name") val drugName: String = "",
    @SerialName("customer_name") val customerName: String = "",
    @SerialName("return_quantity") val returnQuantity: Double = 0.0,
    @SerialName("return_amount") val returnAmount: Double = 0.0,
    @SerialName("return_count") val returnCount: Int = 0,
)
