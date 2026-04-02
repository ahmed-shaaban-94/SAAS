# Ktor
-keep class io.ktor.** { *; }
-dontwarn io.ktor.**

# Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** { *** Companion; }
-keepclasseswithmembers class kotlinx.serialization.json.** { kotlinx.serialization.KSerializer serializer(...); }
-keep,includedescriptorclasses class com.datapulse.android.**$$serializer { *; }
-keepclassmembers class com.datapulse.android.** { *** Companion; }
-keepclasseswithmembers class com.datapulse.android.** { kotlinx.serialization.KSerializer serializer(...); }

# AppAuth
-keep class net.openid.appauth.** { *; }

# Room
-keep class * extends androidx.room.RoomDatabase
-dontwarn androidx.room.paging.**

# Sentry
-keep class io.sentry.** { *; }
-dontwarn io.sentry.**
