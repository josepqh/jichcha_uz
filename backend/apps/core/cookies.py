"""Let the production-settings stack work on plain http://localhost in every browser.

The Docker stack runs production settings, so its cookies carry Secure. Chrome treats
http://localhost as a secure context and keeps them; Safari drops them, so every request looked
like a new guest and a task created a moment earlier answered 404. For loopback hosts over plain
HTTP only, Secure is removed from the response's cookies. Real hosts (and HTTPS) are untouched.
"""

from django.http import HttpRequest, HttpResponse

LOOPBACK = {"localhost", "127.0.0.1", "[::1]", "::1"}


def is_local_plain_http(request: HttpRequest) -> bool:
    if request.is_secure():
        return False
    raw = request.get_host().lower()
    host = raw.split("]")[0] + "]" if raw.startswith("[") else raw.rsplit(":", 1)[0]
    return host in LOOPBACK or host.endswith(".localhost")


class LocalCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if response.cookies and is_local_plain_http(request):
            for morsel in response.cookies.values():
                morsel["secure"] = ""
        return response
