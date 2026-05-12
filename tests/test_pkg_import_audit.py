"""Tests for the device-class registration audit log in devices/base.py."""

import logging

import pytest

from custom_components.abode_security.abode.devices import base
from custom_components.abode_security.abode.devices.base import (
    Device,
    _log_registered_classes_once,
)

EXPECTED_DEVICE_MODULES = {
    "custom_components.abode_security.abode.devices.alarm",
    "custom_components.abode_security.abode.devices.binary_sensor",
    "custom_components.abode_security.abode.devices.camera",
    "custom_components.abode_security.abode.devices.cover",
    "custom_components.abode_security.abode.devices.light",
    "custom_components.abode_security.abode.devices.lock",
    "custom_components.abode_security.abode.devices.sensor",
    "custom_components.abode_security.abode.devices.switch",
    "custom_components.abode_security.abode.devices.valve",
}

_AUDIT_KEY = "abode_security.audit.registered_device_classes="


class TestAuditLog:
    def setup_method(self) -> None:
        from custom_components.abode_security.abode.devices import pkg

        pkg.import_all()
        base._AUDIT_LOGGED = False

    def test_emits_exactly_one_record(self, caplog: pytest.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger=base.log.name):
            _log_registered_classes_once()

        matching = [r for r in caplog.records if _AUDIT_KEY in r.getMessage()]
        assert len(matching) == 1

    def test_all_nine_known_modules_registered(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=base.log.name):
            _log_registered_classes_once()

        record = next(r for r in caplog.records if _AUDIT_KEY in r.getMessage())
        suffix = record.getMessage().split(_AUDIT_KEY, 1)[1]
        registered = set(suffix.split(",")) if suffix else set()

        missing = EXPECTED_DEVICE_MODULES - registered
        assert not missing, f"Missing modules in audit log: {missing}"

    def test_iter_subclasses_returns_at_least_nine(self) -> None:
        from custom_components.abode_security.abode.devices._ancestry import (
            iter_subclasses,
        )

        subclasses = list(iter_subclasses(Device))
        modules = {cls.__module__ for cls in subclasses}
        missing = EXPECTED_DEVICE_MODULES - modules
        assert not missing, f"iter_subclasses missing modules: {missing}"

    def test_sentinel_prevents_second_emission(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=base.log.name):
            _log_registered_classes_once()
            _log_registered_classes_once()

        matching = [r for r in caplog.records if _AUDIT_KEY in r.getMessage()]
        assert len(matching) == 1
