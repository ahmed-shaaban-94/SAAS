package com.datapulse.android

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import io.sentry.android.core.SentryAndroid

@HiltAndroidApp
class DataPulseApp : Application() {

    override fun onCreate() {
        super.onCreate()
        initSentry()
    }

    private fun initSentry() {
        val dsn = BuildConfig.SENTRY_DSN
        if (dsn.isNotBlank()) {
            SentryAndroid.init(this) { options ->
                options.dsn = dsn
                options.environment = if (BuildConfig.DEBUG) "development" else "production"
                options.release = "${BuildConfig.APPLICATION_ID}@${BuildConfig.VERSION_NAME}"
                options.isEnableAutoSessionTracking = true
                options.tracesSampleRate = 0.2
                options.isAttachAnrThreadDump = true
                options.isSendDefaultPii = false
            }
        }
    }
}
