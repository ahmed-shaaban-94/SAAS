package com.datapulse.android.domain.model

data class ExploreDimension(
    val name: String,
    val type: String,
    val description: String?,
)

data class ExploreMetric(
    val name: String,
    val type: String,
    val description: String?,
)

data class ExploreModelInfo(
    val name: String,
    val label: String,
    val description: String?,
    val dimensions: List<ExploreDimension>,
    val metrics: List<ExploreMetric>,
)

data class ExploreCatalog(
    val models: List<ExploreModelInfo>,
)
