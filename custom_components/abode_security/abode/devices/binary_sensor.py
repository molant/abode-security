"""Abode binary sensor device."""

from . import base
from . import status as STATUS


class BinarySensor(base.Device):
    """Class to represent an on / off, online/offline sensor."""

    @property
    def is_on(self):
        """
        Get sensor state.

        Reports the last known status. A status the device never sent (missing
        or empty) is not evidence of activity, and neither is it evidence of
        "clear" — ``is_reporting`` is what tells the two apart.
        """
        if not self.status:
            return False
        return self.status not in (
            STATUS.OFF,
            STATUS.OFFLINE,
            STATUS.CLOSED,
        )

    @property
    def is_reporting(self):
        """
        Whether the device is currently reporting its own state.

        A sensor that has dropped off the RF network keeps the last status it
        managed to send, so ``Offline`` (or a ``no_response`` fault) means that
        status is stale — not that the door is closed. Callers surface this as
        unavailable rather than letting stale state read as "clear", which is
        what turned an offline blip on an open window into a spurious
        "off" -> "on" activation (issue #210).
        """
        return (
            bool(self.status)
            and self.status != STATUS.OFFLINE
            and not self.no_response
        )


#: Tags whose steady-state status is `Online` and whose real events arrive over
#: the timeline rather than through device status. For these `Offline` is the
#: reading itself — they surface with the `connectivity` device class, where
#: `off` renders as "Disconnected" — so withholding it as `unavailable` would
#: erase the only state the entity exists to report.
#:
#: The rest of `Connectivity`'s tags are not like this: `water_sensor` reports
#: `On`/`Off` for moisture, and `smoke_detector`/`fix_panic` are unverified
#: against a real device. Those carry a payload an offline blip must not be
#: allowed to fake, so they take the staleness treatment (issue #210).
_LINK_STATE_TAGS = frozenset(
    f'device_type.{tag}'
    for tag in ('glass', 'keypad', 'remote_controller', 'siren', 'bx')
)


class Connectivity(BinarySensor):
    """Upstream's catch-all for sensors that report `Online` — plus moisture.

    The class is overloaded: most of these tags report their link to the panel
    as their status, but `water_sensor` (and possibly `smoke_detector` /
    `fix_panic`) report a real payload. `is_reporting` splits them by tag
    rather than by class for that reason.
    """

    tags = (
        'glass',
        'keypad',
        'remote_controller',
        'siren',
        # status display
        'bx',
        # moisture
        'water_sensor',
        'fix_panic',
        'smoke_detector',
    )

    @property
    def is_reporting(self):
        """Report always for the tags whose `Offline` is the reading itself."""
        if str(self.get_value('type_tag')).lower() in _LINK_STATE_TAGS:
            return True
        return super().is_reporting


class Motion(BinarySensor):
    tags = (
        'pir',
        'povs',
    )

    @property
    def is_on(self):
        if self.type == 'Occupancy':
            # `STATUS.ONLINE` is a plain string, so `status not in STATUS.ONLINE`
            # was a substring test: "On" read as clear and "Offline" read as
            # occupied. Compare against the statuses themselves, keeping
            # "Offline" clear like every other sensor type (issue #210).
            return bool(self.status) and self.status not in (
                STATUS.ONLINE,
                STATUS.OFFLINE,
            )
        return super().is_on


class Door(BinarySensor):
    tags = ('door_contact',)
