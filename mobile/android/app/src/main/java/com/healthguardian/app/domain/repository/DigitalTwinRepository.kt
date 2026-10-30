package com.healthguardian.app.domain.repository

import com.healthguardian.app.domain.model.DigitalTwin

interface DigitalTwinRepository {

    suspend fun getDigitalTwin(): DigitalTwin
}