"""The dashboard: Django's admin styled with Unfold, at ``/dashboard/`` (design section 11).

It is Django's default admin site (``config.apps.DashboardAdminConfig``), so a module registers
its screens with ``@admin.register`` as usual. On top of Unfold's site it adds:

- Login by role, not ``is_staff``: only super admin, management, reception and supervisor
  (``DashboardBackend`` checks the password with the API's rules).
- Two gates before any other page: a temporary password must be changed first, then a user
  with several dashboard roles chooses the role to act in.
- The role check of every screen (``allows``), read from ``navigation.ROLE_GROUPS``.
- Only ``DashboardModelAdmin`` screens are accepted; each gets ``ReadOnlyForManagement``.
"""

from functools import update_wrapper

from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
from unfold.sites import UnfoldAdminSite

from apps.accounts.models import ROLE_CHOICES
from apps.core.dashboard import DashboardModelAdmin

from .access import choose_role, dashboard_access
from .forms import DashboardLoginForm, DashboardPasswordChangeForm
from .navigation import first_link, model_roles, url_roles
from .permissions import ReadOnlyForManagement

ROLE_NAMES = dict(ROLE_CHOICES)

# Pages that stay open while a gate is closed.
_PASSWORD_GATE_OPEN = frozenset({"logout", "password_change", "password_change_done", "jsi18n"})
_ROLE_GATE_OPEN = _PASSWORD_GATE_OPEN | {"choose_role"}


class DashboardSite(UnfoldAdminSite):
    login_form = DashboardLoginForm
    # The texts come from settings.SPU_BRAND through Unfold's settings.
    index_title = _("Home")
    password_change_template = "dashboard/password_change.html"

    # Who may log in, and to which screens -------------------------------------------

    def has_permission(self, request) -> bool:
        """Logged in and holding at least one dashboard role (``request.user.is_staff`` is not
        used)."""
        return dashboard_access(request) is not None

    def allows(self, request, model, action: str) -> bool:
        """The role check of every screen (``DashboardModelAdmin`` asks it). ``action`` is
        "view", "add" or "change"; the role decides all three, and each screen narrows them
        further (``ReadOnlyForManagement``, read-only screens)."""
        access = dashboard_access(request)
        return (
            access is not None
            and access.active_role is not None
            and not access.must_change_password
            and access.active_role in model_roles(model)
        )

    def register(self, model_or_iterable, admin_class=None, **options):
        admin_class = admin_class or DashboardModelAdmin
        if not issubclass(admin_class, DashboardModelAdmin):
            if admin_class.__module__.startswith("apps."):
                raise ImproperlyConfigured(
                    f"{admin_class.__qualname__} must inherit apps.core.dashboard."
                    "DashboardModelAdmin."
                )
            # Screens of installed libraries (auth groups, Celery beat, token blacklist) have
            # no role check and are not part of the dashboard.
            return
        if not issubclass(admin_class, ReadOnlyForManagement):
            admin_class = type(
                admin_class.__name__,
                (ReadOnlyForManagement, admin_class),
                {"__module__": admin_class.__module__},
            )
        super().register(model_or_iterable, admin_class, **options)

    # The gates ----------------------------------------------------------------------

    def admin_view(self, view, cacheable=False):
        def gated(request, *args, **kwargs):
            access = dashboard_access(request)
            url_name = request.resolver_match.url_name if request.resolver_match else None
            if access is not None:
                if access.must_change_password and url_name not in _PASSWORD_GATE_OPEN:
                    return redirect(f"{self.name}:password_change")
                if access.active_role is None and url_name not in _ROLE_GATE_OPEN:
                    return redirect(f"{self.name}:choose_role")
            return view(request, *args, **kwargs)

        return super().admin_view(update_wrapper(gated, view), cacheable)

    def get_urls(self):
        return [
            path("role/", self.admin_view(self.choose_role_view), name="choose_role"),
            *super().get_urls(),
        ]

    # Pages --------------------------------------------------------------------------

    def each_context(self, request):
        context = super().each_context(request)
        access = dashboard_access(request)
        if access is not None:
            context["active_role_name"] = ROLE_NAMES.get(access.active_role, "")
            context["can_switch_role"] = len(access.roles) > 1
        return context

    def index(self, request, extra_context=None):
        """Home (filled with key figures in P1.11). A role without Home goes to its first
        screen."""
        access = dashboard_access(request)
        if access.active_role not in url_roles(f"{self.name}:index"):
            link = first_link(access.active_role)
            if link is not None:
                return redirect(link)
        context = {
            **self.each_context(request),
            "title": self.index_title,
            "subtitle": None,
            **(extra_context or {}),
        }
        request.current_app = self.name
        return TemplateResponse(request, "dashboard/home.html", context)

    @staticmethod
    def _next_url(request) -> str | None:
        target = request.POST.get("next") or request.GET.get("next")
        if target and url_has_allowed_host_and_scheme(
            target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return target
        return None

    def choose_role_view(self, request):
        """The role to act in, for a user who holds more than one dashboard role (US-04)."""
        return require_http_methods(["GET", "POST"])(self._choose_role)(request)

    def _choose_role(self, request):
        access = dashboard_access(request)
        if request.method == "POST":
            role = request.POST.get("role", "")
            if role not in access.roles:
                raise PermissionDenied
            choose_role(request, role)
            return HttpResponseRedirect(self._next_url(request) or reverse(f"{self.name}:index"))
        roles = [(code, ROLE_NAMES[code]) for code, _name in ROLE_CHOICES if code in access.roles]
        context = {
            **self.each_context(request),
            "title": _("Choose your role"),
            "roles": roles,
            "active_role": access.active_role,
            "next": self._next_url(request) or "",
        }
        request.current_app = self.name
        return TemplateResponse(request, "dashboard/choose_role.html", context)

    def password_change(self, request, extra_context=None):
        """The user's own password, through the ``ChangePassword`` service."""
        defaults = {
            "form_class": DashboardPasswordChangeForm,
            "success_url": reverse(f"{self.name}:password_change_done", current_app=self.name),
            "extra_context": {
                **self.each_context(request),
                "password_change_required": bool(
                    (access := dashboard_access(request)) and access.must_change_password
                ),
                **(extra_context or {}),
            },
        }
        if self.password_change_template is not None:
            defaults["template_name"] = self.password_change_template
        request.current_app = self.name
        return PasswordChangeView.as_view(**defaults)(request)
