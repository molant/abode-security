import logging

from ._itertools import single

log = logging.getLogger(__name__)


class DictAdapter(dict):
    """Adapt a dict for format string with attribute-like access."""

    def __init__(self, mapping):
        self.data = mapping

    def __getitem__(self, key):
        return self.data[key]


class Stateful:
    def __init__(self, state, client):
        """Set up Abode device."""
        self._state = state
        self._client = client

    def __getattr__(self, name):
        try:
            return self._state[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def update(self, state):
        """Update the local state from a new state.

        Only updates keys already present.
        """
        # Only update keys already present in self._state
        projection = {key: state[key] for key in self._state if key in state}
        self._state.update(projection)

    @property
    def desc(self):
        """Return a short description of self."""
        return self._desc_t.format_map(DictAdapter(self))

    async def refresh(self, path=None):
        """Refresh the device state.

        Useful when not using the notification service.
        """
        tmpl = path or self._url_t
        path = tmpl.format(id=self.id)

        response = await self._client.send_request(method="get", path=path)
        state = single(await response.json())

        log.debug(f"{self.__class__.__name__} Refresh Response: %s", await response.text())

        self._validate(state)
        self.update(state)

        return state

    def _validate(self, state):
        pass
