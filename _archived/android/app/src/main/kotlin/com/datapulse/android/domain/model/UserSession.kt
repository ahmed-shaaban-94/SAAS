package com.datapulse.android.domain.model

data class UserSession(
    val sub: String,
    val email: String,
    val preferredUsername: String,
    val tenantId: String,
    val roles: List<String>,
) {
    val isAdmin: Boolean get() = roles.contains("admin")
}
