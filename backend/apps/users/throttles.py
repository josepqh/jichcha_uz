import re

from rest_framework.throttling import SimpleRateThrottle

_RATE = re.compile(r"^(\d+)/(\d*)([smhd])")
_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class AuthRateThrottle(SimpleRateThrottle):
    """Per-IP limit for credential endpoints. Accepts rates like "10/15m"."""

    scope = "auth"

    def parse_rate(self, rate):
        if rate is None:
            return (None, None)
        match = _RATE.match(rate)
        if not match:
            raise ValueError(f"Invalid rate: {rate!r}")
        count, multiplier, unit = match.groups()
        return int(count), int(multiplier or 1) * _SECONDS[unit]

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
