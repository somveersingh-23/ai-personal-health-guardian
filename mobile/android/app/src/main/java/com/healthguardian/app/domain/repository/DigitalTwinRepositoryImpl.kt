package com.healthguardian.app.data.repository

import com.healthguardian.app.data.local.DigitalTwinLocalDataSource
import com.healthguardian.app.domain.model.DigitalTwin
import com.healthguardian.app.domain.repository.DigitalTwinRepository

class DigitalTwinRepositoryImpl(
    private val localDataSource: DigitalTwinLocalDataSource
) : DigitalTwinRepository {

    override suspend fun getDigitalTwin(): DigitalTwin {
        return localDataSource.getDigitalTwin()
    }
}