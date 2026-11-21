"""The dashboard sidebar and who sees which screen (design section 11).

There is one map, ``ROLE_GROUPS``: the sidebar groups each dashboard role sees. Modules do not
decide roles themselves; they register their screens into a group from their ``admin.py``:

    register_screen(Group.FACILITIES, model=Clinic, title=_("Clinics"), icon="apartment")

A screen is shown to, and opens for, the roles whose groups include its group. ``roles``
narrows a screen further (it can never widen the group). The same map decides the menu and
the permission checks of every admin view (``DashboardSite.allows``), so a screen hidden from
a role is also refused when the role types its URL.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from django.db.models import Model
from django.urls import NoReverseMatch, reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from apps.accounts.domain.roles import RoleCode


class Group(StrEnum):
    """Sidebar groups, in the order they are shown."""

    HOME = "home"
    PATIENTS = "patients"
    APPROVALS = "approvals"
    CLINICAL = "clinical"
    SCHEDULING = "scheduling"
    MAINTENANCE = "maintenance"
    STUDENTS = "students"
    ACADEMIC_SETUP = "academic_setup"
    FACILITIES = "facilities"
    LISTS = "lists"
    REPORTS = "reports"
    USERS = "users"
    SETTINGS = "settings"


GROUP_TITLES: Mapping[Group, Promise] = {
    Group.HOME: _("Home"),
    Group.PATIENTS: _("Patients"),
    Group.APPROVALS: _("Approvals"),
    Group.CLINICAL: _("Clinical"),
    Group.SCHEDULING: _("Scheduling"),
    Group.MAINTENANCE: _("Maintenance"),
    Group.STUDENTS: _("Students"),
    Group.ACADEMIC_SETUP: _("Academic setup"),
    Group.FACILITIES: _("Facilities"),
    Group.LISTS: _("Lists"),
    Group.REPORTS: _("Reports"),
    Group.USERS: _("Users"),
    Group.SETTINGS: _("Settings"),
}

# The single role → groups map (design section 11, "What each role sees").
ROLE_GROUPS: Mapping[str, frozenset[Group]] = {
    RoleCode.SUPER_ADMIN: frozenset(Group),
    RoleCode.MANAGEMENT: frozenset(
        {
            Group.HOME,
            Group.PATIENTS,
            Group.CLINICAL,
            Group.SCHEDULING,
            Group.MAINTENANCE,
            Group.REPORTS,
        }
    ),
    RoleCode.RECEPTION: frozenset({Group.PATIENTS}),
    RoleCode.SUPERVISOR: frozenset(
        {
            Group.HOME,
            Group.APPROVALS,
            Group.CLINICAL,
            Group.SCHEDULING,
            Group.STUDENTS,
            Group.REPORTS,
            Group.MAINTENANCE,
        }
    ),
}


def groups_of(role: str | None) -> frozenset[Group]:
    return ROLE_GROUPS.get(role, frozenset()) if role else frozenset()


def roles_of_group(group: Group) -> frozenset[str]:
    return frozenset(role for role, groups in ROLE_GROUPS.items() if group in groups)


@dataclass(frozen=True, slots=True)
class Screen:
    """One sidebar item: a model's list (``model``) or a page (``url_name``)."""

    group: Group
    title: str | Promise
    icon: str
    model: str | None = None  # "app_label.modelname"
    url_name: str | None = None
    only_roles: frozenset[str] | None = None

    @property
    def roles(self) -> frozenset[str]:
        roles = roles_of_group(self.group)
        return roles & self.only_roles if self.only_roles is not None else roles

    def link(self) -> str | None:
        name = self.url_name
        if self.model is not None:
            app_label, model_name = self.model.split(".")
            name = f"admin:{app_label}_{model_name}_changelist"
        try:
            return reverse(name)
        except NoReverseMatch:  # the screen's admin is not registered
            return None


_screens: list[Screen] = []


def _model_label(model: type[Model] | str) -> str:
    return model.lower() if isinstance(model, str) else model._meta.label_lower


def register_screen(
    group: Group,
    *,
    title: str | Promise,
    icon: str,
    model: type[Model] | str | None = None,
    url_name: str | None = None,
    roles: Iterable[str] | None = None,
) -> Screen:
    """Add a screen to a sidebar group. Give either ``model`` (a model class, or
    ``"app_label.ModelName"`` for a model of a module you may not import) or ``url_name``."""
    if (model is None) == (url_name is None):
        raise ValueError("Give either model or url_name.")
    screen = Screen(
        group=Group(group),
        title=title,
        icon=icon,
        model=_model_label(model) if model is not None else None,
        url_name=url_name,
        only_roles=frozenset(roles) if roles is not None else None,
    )
    if screen not in _screens:
        _screens.append(screen)
    return screen


def screens() -> list[Screen]:
    return list(_screens)


def model_roles(model: type[Model] | str) -> frozenset[str]:
    """The roles that may open a model's screens. A model on no screen opens for nobody."""
    label = _model_label(model)
    roles: frozenset[str] = frozenset()
    for screen in _screens:
        if screen.model == label:
            roles |= screen.roles
    return roles


def url_roles(url_name: str) -> frozenset[str]:
    roles: frozenset[str] = frozenset()
    for screen in _screens:
        if screen.url_name == url_name:
            roles |= screen.roles
    return roles


def screens_for(role: str | None) -> list[tuple[Group, list[Screen]]]:
    """The groups a role sees, in sidebar order, each with its screens. Empty groups are left
    out."""
    if not role:
        return []
    result = []
    for group in Group:
        items = [s for s in _screens if s.group == group and role in s.roles]
        if items:
            result.append((group, items))
    return result


def sidebar(request) -> list[dict]:
    """Unfold's ``SIDEBAR["navigation"]`` callback: the groups of the active role."""
    from .access import dashboard_access

    access = dashboard_access(request)
    if access is None:
        return []
    # While a gate is closed, the only item is the page that opens it.
    if access.must_change_password:
        return [_gate_group(_("Change password"), "password", "admin:password_change")]
    if access.active_role is None:
        return [_gate_group(_("Choose your role"), "badge", "admin:choose_role")]
    navigation = []
    for group, items in screens_for(access.active_role):
        links = [
            {"title": screen.title, "icon": screen.icon, "link": link}
            for screen in items
            if (link := screen.link()) is not None
        ]
        if links:
            navigation.append({"title": GROUP_TITLES[group], "separator": True, "items": links})
    return navigation


def _gate_group(title, icon: str, url_name: str) -> dict:
    return {
        "title": _("Your account"),
        "separator": True,
        "items": [{"title": title, "icon": icon, "link": reverse(url_name)}],
    }


def first_link(role: str | None) -> str | None:
    for _group, items in screens_for(role):
        for screen in items:
            if (link := screen.link()) is not None:
                return link
    return None


def account_links(request) -> list[dict]:
    """Unfold's ``ACCOUNT["navigation"]`` callback: "Switch role" for users with several
    dashboard roles."""
    from .access import dashboard_access

    access = dashboard_access(request)
    if access is None or len(access.roles) < 2:
        return []
    return [{"title": _("Switch role"), "link": reverse("admin:choose_role")}]
