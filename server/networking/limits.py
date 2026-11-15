"""Limits that keep one visitor from flooding the server."""

import time
from collections import deque
from typing import Deque, Dict, Optional


class Refused(ValueError):
    """A request turned down for a reason the app can name to the player (`code`)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class RateLimit:
    """At most `count` events within `seconds`, per key (an address or a player)."""

    def __init__(self, count: int, seconds: float):
        self.count = count
        self.seconds = seconds
        self.hits: Dict[str, Deque[float]] = {}

    def check(self, key: str, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        hits = self.hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.seconds:
            hits.popleft()
        if len(hits) >= self.count:
            raise Refused("RATE_LIMITED", "Too many requests, please wait a moment")
        hits.append(now)

    def prune(self, now: Optional[float] = None) -> None:
        """Forget keys with nothing recent (called now and then, so the table does not grow forever)."""
        now = time.monotonic() if now is None else now
        for key in [k for k, hits in self.hits.items() if not hits or now - hits[-1] >= self.seconds]:
            del self.hits[key]


def client_address(environ: dict) -> str:
    """The visitor's address; behind the ingress it is the first entry of X-Forwarded-For."""
    forwarded = (environ.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    return forwarded or environ.get("REMOTE_ADDR") or "unknown"
