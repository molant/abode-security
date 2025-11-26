import builtins


class Exception(builtins.Exception):
    """Class to throw general abode exception."""

    def __init__(self, error):
        super().__init__(*error)

    @property
    def errcode(self):
        code, _ = self.args
        return code

    @property
    def message(self):
        _, message = self.args
        return message


class AuthenticationException(Exception):
    """Class to throw authentication exception."""

    @classmethod
    async def raise_for(cls, response):
        if response.status >= 400:
            message = await cls.best_message(response)
            retry_after = response.headers.get('Retry-After')
            retry_after_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None

            if response.status == 429:
                raise RateLimitException((response.status, message), retry_after_seconds)

            raise cls((response.status, message))

    @staticmethod
    async def best_message(response):
        if response.headers.get('Content-Type') == 'application/json':
            body = await response.json()
            return body.get('message', 'Unknown error')
        return await response.text()


class SocketIOException(Exception):
    """Class to throw SocketIO Error exception."""

    def __init__(self, error, details):
        super().__init__(error)
        self.details = details


class RateLimitException(AuthenticationException):
    """Raised when Abode returns HTTP 429."""

    def __init__(self, error, retry_after=None):
        super().__init__(error)
        self.retry_after = retry_after
