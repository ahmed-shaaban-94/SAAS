package com.datapulse.android.di

import android.content.Context
import com.datapulse.android.data.auth.AuthManager
import com.datapulse.android.data.auth.TokenStore
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AuthModule {

    @Provides
    @Singleton
    fun provideTokenStore(@ApplicationContext context: Context): TokenStore =
        TokenStore(context)

    @Provides
    @Singleton
    fun provideAuthManager(
        @ApplicationContext context: Context,
        tokenStore: TokenStore,
    ): AuthManager = AuthManager(context, tokenStore)
}
