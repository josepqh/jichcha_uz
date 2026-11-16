"""Rate limits for starting conversions.

Many people in Uzbekistan share one public IP (mobile CGNAT, offices, dormitories), so the main
limit follows the account or the guest cookie. A looser per-IP ceiling for guests stops someone
from dodging it by clearing cookies.
"""

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from .identity import guest_key_from_cookie


class TaskCreateThrottle(SimpleRateThrottle):
    """Per account or guest browser. A guest's first request (no cookie yet) is left to the IP ceiling."""

    scope = "task_create"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = f"u:{request.user.pk}"
        else:
            guest_key = guest_key_from_cookie(request)
            if not guest_key:
                return None
            ident = f"g:{guest_key}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class GuestTaskCreateIPThrottle(SimpleRateThrottle):
    """Shared ceiling for all guests behind one IP. Signed-in users are not counted here."""

    scope = "task_create_ip"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class GuestRateThrottle(SimpleRateThrottle):
    """General limit for anonymous requests, per guest browser (status polling is ~60/min per task).

    Requests without a guest cookie fall back to the IP. Replaces DRF's per-IP AnonRateThrottle,
    which would let two people converting behind one CGNAT address block each other.
    """

    scope = "anon"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        guest_key = guest_key_from_cookie(request)
        ident = f"g:{guest_key}" if guest_key else f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AnonIPRateThrottle(SimpleRateThrottle):
    """Ceiling for all anonymous traffic from one IP, whatever the cookies say."""

    scope = "anon_ip"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class SignedInUserRateThrottle(UserRateThrottle):
    """DRF's UserRateThrottle, minus its per-IP fallback for anonymous requests.

    The stock class keys anonymous requests by IP, which would put one shared cap on every guest
    behind a CGNAT address; guests are covered by GuestRateThrottle and AnonIPRateThrottle instead.
    """

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return super().get_cache_key(request, view)
