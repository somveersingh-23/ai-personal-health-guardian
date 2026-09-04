package com.healthguardian.sensor.ble

import android.Manifest
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothProfile
import android.bluetooth.BluetoothStatusCodes
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import java.time.Instant
import java.util.UUID

/**
 * Thin Android GATT transport. The caller obtains [BluetoothDevice] from a user-visible scanner
 * and must never persist its address. Only evidence-declared notification UUIDs are enabled.
 */
class AndroidBleGattTransport(
    private val context: Context,
    private val connector: BleResearchConnector,
    private val onFrame: (BleResearchFrame) -> Unit,
    private val onTransportIssue: (String) -> Unit,
) {
    private var gatt: BluetoothGatt? = null

    @Suppress("MissingPermission", "DEPRECATION")
    fun connect(device: BluetoothDevice) {
        requirePermissions()
        check(connector.state == BleSessionState.READY_TO_CONNECT) {
            "prepare an evidence-backed BLE session before connecting"
        }
        closeGattOnly()
        gatt = device.connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE)
            ?: throw IllegalStateException("Bluetooth LE GATT connection could not be created")
    }

    @Suppress("MissingPermission")
    fun disconnect() {
        gatt?.disconnect()
        closeGattOnly()
        connector.disconnect()
    }

    private val callback = object : BluetoothGattCallback() {
        @Suppress("MissingPermission")
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                fail("gatt_connection_status_$status")
                return
            }
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                runCatching {
                    connector.markConnected()
                    check(gatt.discoverServices()) { "service_discovery_not_started" }
                }.onFailure { fail("gatt_connection_setup_failed") }
            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                connector.disconnect()
                closeGattOnly()
            }
        }

        @Suppress("MissingPermission")
        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                fail("gatt_service_discovery_status_$status")
                return
            }
            for (binding in connector.declaredBindings()) {
                val service = gatt.getService(UUID.fromString(binding.serviceUuid))
                    ?: return fail("declared_gatt_service_missing")
                val characteristic = service.getCharacteristic(UUID.fromString(binding.characteristicUuid))
                    ?: return fail("declared_gatt_characteristic_missing")
                if (!gatt.setCharacteristicNotification(characteristic, true)) {
                    return fail("gatt_notification_enable_failed")
                }
                val descriptor = characteristic.getDescriptor(CLIENT_CHARACTERISTIC_CONFIGURATION_UUID)
                    ?: return fail("gatt_notification_descriptor_missing")
                if (!writeNotificationDescriptor(gatt, descriptor)) {
                    return fail("gatt_notification_descriptor_write_failed")
                }
            }
        }

        override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
            if (status != BluetoothGatt.GATT_SUCCESS) fail("gatt_notification_descriptor_status_$status")
        }

        @Suppress("DEPRECATION")
        @Deprecated("Deprecated in API 33")
        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
        ) {
            accept(characteristic.uuid.toString(), characteristic.value ?: ByteArray(0))
        }

        override fun onCharacteristicChanged(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            value: ByteArray,
        ) {
            accept(characteristic.uuid.toString(), value)
        }
    }

    private fun accept(characteristicUuid: String, payload: ByteArray) {
        runCatching {
            connector.acceptNotification(characteristicUuid, payload, Instant.now())
        }.onSuccess(onFrame).onFailure { fail("undeclared_or_invalid_gatt_notification") }
    }

    @Suppress("MissingPermission", "DEPRECATION")
    private fun writeNotificationDescriptor(
        gatt: BluetoothGatt,
        descriptor: BluetoothGattDescriptor,
    ): Boolean = if (Build.VERSION.SDK_INT >= 33) {
        gatt.writeDescriptor(
            descriptor,
            BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE,
        ) == BluetoothStatusCodes.SUCCESS
    } else {
        descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
        gatt.writeDescriptor(descriptor)
    }

    private fun requirePermissions() {
        val required = if (Build.VERSION.SDK_INT >= 31) {
            listOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
        } else {
            listOf(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        check(required.all { context.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }) {
            "required Bluetooth permissions are not granted"
        }
    }

    @Suppress("MissingPermission")
    private fun fail(code: String) {
        onTransportIssue(code)
        gatt?.disconnect()
        closeGattOnly()
        connector.disconnect()
    }

    @Suppress("MissingPermission")
    private fun closeGattOnly() {
        gatt?.close()
        gatt = null
    }

    private companion object {
        val CLIENT_CHARACTERISTIC_CONFIGURATION_UUID: UUID =
            UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    }
}
