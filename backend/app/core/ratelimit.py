"""Shared SlowAPI rate limiter (per client IP).

Imported by main.py (to register handler/state) and by individual routers
that decorate sensitive endpoints with @limiter.limit("N/minute").
Degrades to a no-op if slowapi isn't installed so the app never fails to boot.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    SLOWAPI_AVAILABLE = True
except Exception as exc:  # pragma: no cover - defensive
    logger.warning("slowapi not available, rate limiting disabled: %s", exc)
    SLOWAPI_AVAILABLE = False

    class _NoopLimiter:
        def limit(self, *_args, **_kwargs):
            def deco(func):
                return func
            return deco

    limiter = _NoopLimiter()  # type: ignore
