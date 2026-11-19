"""Only the Vercel edge may use the public tunnel host.

When the site runs on Vercel with the API behind a tunnel (compose.tunnel.yaml), the tunnel's own
address is public too. Requests to it that skip Vercel could send any X-Forwarded-For and so slip
past the per-IP limits. The Vercel middleware adds a shared secret header; requests for the tunnel
host without it are refused. Other hosts (localhost, the bot calling "backend") are not affected.
"""

import hmac

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

HEADER = "HTTP_X_UNIVERSE_EDGE"


class EdgeSecretMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        host, secret = settings.EDGE_HOST, settings.EDGE_SECRET
        if host and secret and request.get_host().split(":")[0].lower() == host.lower():
            if not hmac.compare_digest(request.META.get(HEADER, ""), secret):
                return JsonResponse(
                    {"error": {"code": "permission_denied", "message": "Use the website.", "details": {}}},
                    status=403,
                )
        return self.get_response(request)
