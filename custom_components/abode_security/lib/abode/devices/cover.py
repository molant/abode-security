"""Abode cover device."""

from . import status as STATUS
from .switch import Switch


class Cover(Switch):
    """Class to add cover functionality."""

    tags = ('secure_barrier',)

    async def switch_on(self):
        """Turn the switch on."""
        await self.set_status(int(STATUS.OPEN))
        self._state['status'] = STATUS.OPEN

    async def switch_off(self):
        """Turn the switch off."""
        await self.set_status(int(STATUS.CLOSED))
        self._state['status'] = STATUS.CLOSED

    async def open_cover(self):
        """Open the cover."""
        return await self.switch_on()

    async def close_cover(self):
        """Close the cover."""
        return await self.switch_off()

    @property
    def is_open(self):
        """Get if the cover is open."""
        return self.is_on

    @property
    def is_on(self):
        """
        Get cover state.

        Assume cover is open.
        """
        return self.status not in STATUS.CLOSED
