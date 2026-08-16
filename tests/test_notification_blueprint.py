"""Render the bundled notification blueprint's templates for real.

The blueprint decides whether a notification bypasses Do Not Disturb, so its
Jinja is safety-relevant and easy to get subtly wrong — a template variable
rendering the *string* "False" is truthy in Jinja, which is why the escalation
decision is a string comparison rather than a boolean. These tests run the
templates through Home Assistant's own engine so that trap stays closed.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml
from homeassistant.helpers.template import Template

BLUEPRINT = (
    Path(__file__).parent.parent / "blueprints" / "abode_security_notification.yaml"
)


class _InputLoader(yaml.SafeLoader):
    """SafeLoader that tolerates HA's `!input` tag."""


_InputLoader.add_constructor(
    "!input", lambda loader, node: f"__input__{loader.construct_scalar(node)}"
)


def _blueprint() -> dict[str, Any]:
    return yaml.load(BLUEPRINT.read_text(), Loader=_InputLoader)


def _event(**overrides: Any) -> dict[str, Any]:
    """A representative action_triggered payload."""
    data = {
        "action_id": "9ec92f6b-390a-4710-9b55-4083f3ada640",
        "action_name": "Call the police",
        "triggered_by": "binary_sensor.upstairs_animal_detected",
        "mode": "away",
        "alarms_triggered": ["switch.abode_alarm_panic_alarm"],
        "alarms_failed": [],
        "alarm_outcome": "armed",
        "alarm_failures": {},
        "severity": "critical",
        "timestamp": "2026-08-14T12:39:53.545375+00:00",
        "sensor_friendly_name": "Upstairs Animal Detected",
        "sensor_device_class": "motion",
        "previous_state": "off",
        "new_state": "on",
        "sensor_area_id": None,
        "sensor_area_name": None,
        "camera_entity_id": "camera.g4_instant_high_resolution_channel",
        "snapshot_path": "/local/abode_security_snapshots/x.jpg",
        "snapshot_error": None,
    }
    data.update(overrides)
    return data


def _render_notify_data(hass, scope: dict[str, Any]) -> dict[str, Any]:
    """Render the final `data:` payload the notify service receives.

    Deliberately reads the template out of the blueprint rather than
    reimplementing the merge, so a change to how the three dicts are combined
    is covered here. The merge avoids HA's `combine` filter, which needs
    2024.10+ while the integration declares a 2024.1 floor.
    """
    notify_step = _blueprint()["action"][1]
    tmpl = notify_step["data"]["data"]
    return Template(tmpl, hass).async_render(scope, parse_result=True)


def _render(
    hass, event_data: dict[str, Any], critical_mode: str = "auto"
) -> dict[str, Any]:
    """Evaluate the blueprint's `variables:` block the way a script would.

    Each variable is rendered in order against the accumulating scope, which
    is what Home Assistant's script engine does for a `variables:` step.
    """
    variables = _blueprint()["action"][0]["variables"]
    scope: dict[str, Any] = {
        "trigger": {"event": {"data": event_data}},
        "critical_mode": critical_mode,
        "action_filter": "",
    }
    for name, tmpl in variables.items():
        scope[name] = Template(tmpl, hass).async_render(scope, parse_result=True)
    return scope


@pytest.mark.parametrize(
    ("severity", "critical_mode", "expect_level"),
    [
        ("critical", "auto", "critical"),
        ("high", "auto", "time-sensitive"),
        ("normal", "auto", None),
        ("normal", "always", "critical"),
        ("critical", "never", None),
        ("high", "never", None),
    ],
)
async def test_escalation_matrix(hass, severity, critical_mode, expect_level) -> None:
    """severity + critical_mode decide the iOS interruption level."""
    scope = _render(hass, _event(severity=severity), critical_mode)
    push = scope["push_data"].get("push", {}) if scope["push_data"] else {}
    assert push.get("interruption-level") == expect_level


async def test_critical_carries_the_full_ios_and_android_payload(hass) -> None:
    """A critical alert needs the sound dict *and* the Android channel keys."""
    scope = _render(hass, _event(severity="critical"))
    data = scope["push_data"]
    assert data["push"]["sound"] == {"name": "default", "critical": 1, "volume": 1.0}
    assert data["channel"] == "critical"
    assert data["priority"] == "high"
    assert data["ttl"] == 0


async def test_push_mode_never_leaks_a_truthy_false_string(hass) -> None:
    """Regression guard for the "False" -is-truthy Jinja trap.

    If push_mode were a boolean-rendering template, a `normal` severity would
    still escalate, because the string "False" is truthy.
    """
    scope = _render(hass, _event(severity="normal"))
    assert scope["push_mode"].strip() == "none"
    assert scope["push_data"] == {}


async def test_failed_alarm_is_announced_in_title_and_message(hass) -> None:
    """The incident case: the action fired but Abode refused the alarm."""
    scope = _render(
        hass,
        _event(
            alarms_triggered=[],
            alarms_failed=["switch.abode_alarm_burglar_alarm"],
            alarm_outcome="failed",
            alarm_failures={
                "switch.abode_alarm_burglar_alarm": "api_error: (400, 'invalid value')"
            },
            severity="critical",
        ),
    )
    assert scope["title_text"].startswith("⚠️ ALARM FAILED —")
    assert "monitoring was NOT contacted" in scope["message_text"]
    # ...and it must still be loud.
    assert scope["push_data"]["push"]["interruption-level"] == "critical"


async def test_armed_alarm_says_so(hass) -> None:
    scope = _render(hass, _event())
    assert not scope["title_text"].startswith("⚠️")
    assert "Alarm raised." in scope["message_text"]


async def test_notification_only_action_is_not_critical(hass) -> None:
    """No alarm configured → normal severity, no escalation, no scary title."""
    scope = _render(
        hass,
        _event(
            alarms_triggered=[],
            alarm_outcome="none",
            severity="normal",
            mode="home",
        ),
    )
    assert scope["push_data"] == {}
    assert not scope["title_text"].startswith("⚠️")
    assert "Alarm raised." not in scope["message_text"]


async def test_deep_link_always_present(hass) -> None:
    """Tapping must land somewhere even when no camera was resolved.

    The previous `choose` matrix emitted no `data:` block at all in that case,
    so the notification was completely untappable.
    """
    with_camera = _render(hass, _event())["link_data"]
    assert with_camera["url"].endswith(
        "&camera=camera.g4_instant_high_resolution_channel"
    )
    assert with_camera["clickAction"] == with_camera["url"]

    without = _render(hass, _event(camera_entity_id=None))["link_data"]
    assert without["url"] == "/abode_security?tab=cameras"


async def test_image_omitted_rather_than_null(hass) -> None:
    """Some notify integrations reject `image: null`, so the key must vanish."""
    assert "image" not in _render(hass, _event(snapshot_path=None))["image_data"]
    assert _render(hass, _event())["image_data"]["image"].startswith("/local/")


async def test_snapshot_error_is_surfaced(hass) -> None:
    """snapshot_error was on the event from the start and never rendered."""
    scope = _render(hass, _event(snapshot_path=None, snapshot_error="timeout"))
    assert "snapshot unavailable: timeout" in scope["message_text"]


async def test_merged_notify_payload_is_a_real_dict(hass) -> None:
    """The three parts must merge into one flat dict for the notify service."""
    scope = _render(hass, _event(severity="critical"))
    data = _render_notify_data(hass, scope)

    assert isinstance(data, dict)
    assert data["image"].startswith("/local/")
    assert data["url"].startswith("/abode_security?tab=cameras")
    assert data["clickAction"] == data["url"]
    assert data["push"]["interruption-level"] == "critical"
    assert data["channel"] == "critical"
    assert data["ttl"] == 0


async def test_merged_payload_omits_absent_parts(hass) -> None:
    """No snapshot and no escalation → link keys only, and no `image: null`."""
    scope = _render(
        hass,
        _event(snapshot_path=None, camera_entity_id=None, severity="normal"),
    )
    data = _render_notify_data(hass, scope)

    assert isinstance(data, dict)
    assert set(data) == {"url", "clickAction"}
    assert data["url"] == "/abode_security?tab=cameras"


async def test_legacy_payload_without_severity_keys(hass) -> None:
    """An event fired by an older version must not crash the automation."""
    legacy = _event()
    del legacy["severity"]
    del legacy["alarm_outcome"]
    scope = _render(hass, legacy)
    assert scope["push_data"] == {}
    assert not scope["title_text"].startswith("⚠️")
