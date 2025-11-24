"""Shared constants for all tests."""

from __future__ import annotations

# Domain
DOMAIN = "abode_security"

# Device IDs from fixtures
ALARM_DEVICE_ID = "area_1"  # Alarm/control panel
DEVICE_ID = "0012a4d3614cb7e2b8c9abea31d2fb2a"  # Switch device
AUTOMATION_ID = "1"  # First automation
LIGHT_DEVICE_ID = "123abc"  # Light device
LOCK_DEVICE_ID = "456def"  # Lock device
BINARY_SENSOR_DEVICE_ID = "789ghi"  # Binary sensor device
CAMERA_DEVICE_ID = "012jkl"  # Camera device
COVER_DEVICE_ID = "345mno"  # Cover device
SENSOR_DEVICE_ID = "678pqr"  # Sensor device

# Unique IDs
ALARM_UID = "001122334455"
DEVICE_UID = "0012a4d3614cb7e2b8c9abea31d2fb2a"
AUTOMATION_UID = "47fae27488f74f55b964a81a066c3a01"
LIGHT_UID = "123abc-light"
LOCK_UID = "456def-lock"
BINARY_SENSOR_UID = "789ghi-binary"
CAMERA_UID = "012jkl-camera"
COVER_UID = "345mno-cover"
SENSOR_UID = "678pqr-sensor"

# Entity IDs
ALARM_ENTITY_ID = "alarm_control_panel.abode_alarm"
DEVICE_ENTITY_ID = "switch.test_switch"
AUTOMATION_ENTITY_ID = "switch.test_automation"
PANIC_ALARM_ENTITY_ID = "switch.test_alarm_panic_alarm"
TEST_MODE_ENTITY_ID = "switch.test_alarm_test_mode"
LIGHT_ENTITY_ID = "light.test_light"
LOCK_ENTITY_ID = "lock.test_lock"
BINARY_SENSOR_ENTITY_ID = "binary_sensor.test_sensor"
CAMERA_ENTITY_ID = "camera.test_camera"
COVER_ENTITY_ID = "cover.test_cover"
SENSOR_ENTITY_ID = "sensor.test_sensor"
