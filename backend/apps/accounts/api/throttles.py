"""Rate limits (design section 8): login 10 a minute per IP. Every other endpoint uses DRF's
``UserRateThrottle`` (120 a minute per user), set as the default in settings."""

from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
