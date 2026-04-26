package com.datapulse.android.domain.model

sealed class Resource<out T> {
    data class Loading<T>(val cached: T? = null) : Resource<T>()
    data class Success<T>(val data: T, val fromCache: Boolean = false) : Resource<T>()
    data class Error<T>(val message: String, val cached: T? = null) : Resource<T>()
}
