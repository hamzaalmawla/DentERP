"""Arabic by default on the dashboard (US-04, SYS-07).

``LocaleMiddleware`` follows the browser's ``Accept-Language``, which is right for the API (the
app sends the user's language). On the dashboard the language is Arabic until the user picks
another one with the language switch (which sets Django's language cookie). Place this
middleware right after ``LocaleMiddleware``.
"""

from django.conf import settings
from django.urls import reverse
from django.utils import translation


class DashboardLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._prefix: str | None = None

    def __call__(self, request):
        if self._is_dashboard(request) and settings.LANGUAGE_COOKIE_NAME not in request.COOKIES:
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = translation.get_language()
        return self.get_response(request)

    def _is_dashboard(self, request) -> bool:
        if self._prefix is None:
            self._prefix = reverse("admin:index")
        return request.path_info.startswith(self._prefix)
