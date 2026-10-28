import hashlib
import hmac
import time
from uuid import UUID


class UrlSigner:
    """HMAC-signed, expiring download links. The key stays on the server."""

    def __init__(self, key: str, ttl_seconds: int) -> None:
        self._key = key.encode()
        self._ttl = ttl_seconds

    def expires_at(self, now: float | None = None) -> int:
        # Round up to the next TTL window so a link is stable (cacheable) within a window
        current = int(now if now is not None else time.time())
        return (current // self._ttl + 2) * self._ttl

    def sign(self, attachment_id: UUID, expires: int) -> str:
        message = f"{attachment_id}:{expires}".encode()
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def verify(self, attachment_id: UUID, expires: int, signature: str, now: float | None = None) -> bool:
        if expires < (now if now is not None else time.time()):
            return False
        return hmac.compare_digest(self.sign(attachment_id, expires), signature)
