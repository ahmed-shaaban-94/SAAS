package com.datapulse.android.di

import com.datapulse.android.data.repository.AnalyticsRepositoryImpl
import com.datapulse.android.data.repository.AuthRepositoryImpl
import com.datapulse.android.data.repository.PipelineRepositoryImpl
import com.datapulse.android.domain.repository.AnalyticsRepository
import com.datapulse.android.domain.repository.AuthRepository
import com.datapulse.android.domain.repository.PipelineRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {

    @Binds
    @Singleton
    abstract fun bindAnalyticsRepository(impl: AnalyticsRepositoryImpl): AnalyticsRepository

    @Binds
    @Singleton
    abstract fun bindPipelineRepository(impl: PipelineRepositoryImpl): PipelineRepository

    @Binds
    @Singleton
    abstract fun bindAuthRepository(impl: AuthRepositoryImpl): AuthRepository
}
