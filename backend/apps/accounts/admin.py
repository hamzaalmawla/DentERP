"""Dashboard screens for accounts (DB-02, DB-17): users, roles and the audit log menu item.

Every change goes through an accounts service (CreateUser, UpdateUser, AssignRoles,
ResetPassword, UnlockAccount, DeactivateUser); nothing here saves a model itself. Only the
system administrator opens these screens (``Group.USERS``), and the services check it again.
"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from apps.core import container as core_container
from apps.core.api.errors import localized_message
from apps.core.dashboard import DashboardModelAdmin
from apps.core.domain.errors import DomainError

from . import container
from .application.services import (
    AssignRolesCommand,
    CreateUserCommand,
    UpdateUserCommand,
)
from .dashboard import Group, ReadOnlyForManagement, dashboard_actor, register_screen
from .dashboard.forms import add_service_error
from .models import ROLE_CHOICES, Role, User, UserRole

ROLE_NAMES = dict(ROLE_CHOICES)

# Which form field shows each service error.
_ERROR_FIELDS = {
    "username_taken": "username",
    "username_invalid": "username",
    "university_id_taken": "university_id",
    "full_name_required": "full_name_ar",
    "role_required": "roles",
    "unknown_role": "roles",
    "own_admin_role": "roles",
}


def _roles_field() -> forms.MultipleChoiceField:
    return forms.MultipleChoiceField(
        label=_("Roles"),
        choices=ROLE_CHOICES,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
    )


class _ServiceForm(forms.ModelForm):
    """A user form whose ``clean()`` calls the services. The model is never validated or
    saved by the form: the services hold the rules."""

    actor = None  # set by UserAdmin.get_form

    def _post_clean(self):
        pass


class UserCreateForm(_ServiceForm):
    roles = _roles_field()
    result = None

    class Meta:
        model = User
        fields = ("username", "full_name_ar", "full_name_en", "phone", "university_id")

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        try:
            self.result = container.create_user().execute(
                self.actor,
                CreateUserCommand(
                    username=cleaned["username"],
                    full_name_ar=cleaned["full_name_ar"],
                    full_name_en=cleaned.get("full_name_en") or "",
                    phone=cleaned.get("phone") or "",
                    university_id=cleaned.get("university_id") or "",
                    roles=cleaned["roles"],
                ),
            )
        except DomainError as error:
            add_service_error(self, error, _ERROR_FIELDS)
        return cleaned


class UserChangeForm(_ServiceForm):
    roles = _roles_field()

    class Meta:
        model = User
        fields = ("full_name_ar", "full_name_en", "phone", "university_id")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "roles" in self.fields and self.instance.pk and self.instance.is_active:
            self.fields["roles"].initial = list(
                container.get_profile().execute(self.instance.pk).roles
            )

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        user_id = self.instance.pk
        try:
            # Both changes or neither.
            with core_container.unit_of_work():
                container.update_user().execute(
                    self.actor,
                    UpdateUserCommand(
                        user_id=user_id,
                        full_name_ar=cleaned["full_name_ar"],
                        full_name_en=cleaned.get("full_name_en") or "",
                        phone=cleaned.get("phone") or "",
                        university_id=cleaned.get("university_id") or "",
                    ),
                )
                if "roles" in self.changed_data:
                    container.assign_roles().execute(
                        self.actor, AssignRolesCommand(user_id, cleaned["roles"])
                    )
        except DomainError as error:
            add_service_error(self, error, _ERROR_FIELDS)
        return cleaned


def _active_user_or_none(object_id) -> User | None:
    if not str(object_id).isdigit():
        return None
    return User.objects.filter(pk=int(object_id)).first()


class RoleListFilter(admin.SimpleListFilter):
    title = _("role")
    parameter_name = "role"

    def lookups(self, request, model_admin):
        return ROLE_CHOICES

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                user_roles__role__code=self.value(), user_roles__is_active=True
            ).distinct()
        return queryset


class LockedListFilter(admin.SimpleListFilter):
    title = _("locked")
    parameter_name = "locked"

    def lookups(self, request, model_admin):
        return [("yes", _("Locked now"))]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(locked_until__gt=timezone.now())
        return queryset


@admin.register(User)
class UserAdmin(ReadOnlyForManagement, DashboardModelAdmin):
    list_display = (
        "username",
        "full_name_ar",
        "full_name_en",
        "roles",
        "status",
        "last_login",
    )
    search_fields = ("username", "full_name_ar", "full_name_en", "university_id", "phone")
    list_filter = (RoleListFilter, "is_active", LockedListFilter)
    ordering = ("username",)
    actions = ["unlock_selected"]
    actions_detail = ["reset_password_action", "unlock_action", "deactivate_action"]
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "full_name_ar",
                    "full_name_en",
                    "phone",
                    "university_id",
                    "roles",
                )
            },
        ),
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "username",
                    "full_name_ar",
                    "full_name_en",
                    "phone",
                    "university_id",
                    "roles",
                )
            },
        ),
        (
            _("Login"),
            {
                "fields": (
                    "is_active",
                    "must_change_password",
                    "failed_logins",
                    "locked_until",
                    "last_login",
                )
            },
        ),
    )
    change_readonly_fields = (
        "username",
        "is_active",
        "must_change_password",
        "failed_logins",
        "locked_until",
        "last_login",
    )

    def get_queryset(self, request):
        # Deactivated users are listed too (filter "active"), read-only.
        return User.all_objects.prefetch_related(
            Prefetch(
                "user_roles",
                queryset=UserRole.objects.filter(role__is_active=True).select_related("role"),
                to_attr="active_user_roles",
            )
        )

    def get_fieldsets(self, request, obj=None):
        return self.add_fieldsets if obj is None else self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        return () if obj is None else self.change_readonly_fields

    def get_form(self, request, obj=None, change=False, **kwargs):
        kwargs["form"] = UserChangeForm if obj is not None else UserCreateForm
        form = super().get_form(request, obj, change=change, **kwargs)
        form.actor = dashboard_actor(request)  # a new form class on every call
        return form

    def has_change_permission(self, request, obj=None):
        # A deactivated user is shown read-only.
        return super().has_change_permission(request, obj) and (
            not isinstance(obj, User) or obj.is_active
        )

    def has_manage_account_permission(self, request, object_id=None):
        """For the reset, unlock and deactivate buttons: an active user, and the right to
        change users."""
        if not self.has_change_permission(request):
            return False
        return object_id is None or _active_user_or_none(object_id) is not None

    # Saving: the form's services already did the work --------------------------------

    def save_form(self, request, form, change):
        if not change:
            request._temporary_password_result = form.result
            return User.objects.get(pk=form.result.user.id)
        return User.objects.get(pk=form.instance.pk)

    def save_model(self, request, obj, form, change):
        pass

    def save_related(self, request, form, formsets, change):
        pass

    def response_add(self, request, obj, post_url_continue=None):
        result = request._temporary_password_result
        return self._temporary_password_page(
            request, obj, result, _("The user was created with these login details.")
        )

    # Columns ------------------------------------------------------------------------

    @display(description=_("Roles"))
    def roles(self, obj):
        rows = getattr(obj, "active_user_roles", None)
        if rows is None:
            rows = obj.user_roles.filter(role__is_active=True).select_related("role")
        return "، ".join(str(ROLE_NAMES.get(row.role.code, row.role.code)) for row in rows) or "—"

    @display(
        description=_("Status"),
        label={_("Active"): "success", _("Locked"): "warning", _("Deactivated"): "danger"},
    )
    def status(self, obj):
        if not obj.is_active:
            return _("Deactivated")
        if obj.locked_until and obj.locked_until > timezone.now():
            return _("Locked")
        return _("Active")

    # Actions ------------------------------------------------------------------------

    @admin.action(description=_("Unlock the selected accounts"), permissions=["change"])
    def unlock_selected(self, request, queryset):
        actor = dashboard_actor(request)
        unlocked = 0
        for user_id in queryset.filter(is_active=True, locked_until__gt=timezone.now()).values_list(
            "pk", flat=True
        ):
            try:
                container.unlock_account().execute(actor, user_id)
                unlocked += 1
            except DomainError as error:
                self.message_user(request, localized_message(error), messages.ERROR)
        self.message_user(
            request, _("Accounts unlocked: %(count)d.") % {"count": unlocked}, messages.SUCCESS
        )

    @action(
        description=_("Reset password"),
        url_path="reset-password",
        icon="lock_reset",
        permissions=["manage_account"],
    )
    def reset_password_action(self, request, object_id):
        user = self._active_user(object_id)
        if request.method != "POST":
            return self._confirm_page(
                request,
                user,
                _("Give %(name)s a new temporary password? Their current password stops working.")
                % {"name": user},
                _("Reset password"),
            )
        try:
            result = container.reset_password().execute(dashboard_actor(request), user.pk)
        except DomainError as error:
            return self._back_with_error(request, user, error)
        return self._temporary_password_page(
            request, user, result, _("The password was reset. The account is also unlocked.")
        )

    @action(
        description=_("Unlock account"),
        url_path="unlock",
        icon="lock_open",
        permissions=["manage_account"],
    )
    def unlock_action(self, request, object_id):
        user = self._active_user(object_id)
        if request.method != "POST":
            return self._confirm_page(
                request,
                user,
                _("Unlock the account of %(name)s?") % {"name": user},
                _("Unlock account"),
            )
        try:
            container.unlock_account().execute(dashboard_actor(request), user.pk)
        except DomainError as error:
            return self._back_with_error(request, user, error)
        self.message_user(request, _("The account was unlocked."), messages.SUCCESS)
        return HttpResponseRedirect(self._change_url(user))

    @action(
        description=_("Deactivate user"),
        url_path="deactivate",
        icon="person_off",
        permissions=["manage_account"],
    )
    def deactivate_action(self, request, object_id):
        user = self._active_user(object_id)
        if request.method != "POST":
            return self._confirm_page(
                request,
                user,
                _(
                    "Deactivate %(name)s? They can no longer log in, and they are logged out "
                    "of the app. Their records are kept."
                )
                % {"name": user},
                _("Deactivate user"),
                danger=True,
            )
        try:
            container.deactivate_user().execute(dashboard_actor(request), user.pk)
        except DomainError as error:
            return self._back_with_error(request, user, error)
        self.message_user(request, _("The user was deactivated."), messages.SUCCESS)
        return HttpResponseRedirect(reverse("admin:accounts_user_changelist"))

    # Helpers ------------------------------------------------------------------------

    @staticmethod
    def _active_user(object_id) -> User:
        user = _active_user_or_none(object_id)
        if user is None:
            raise Http404
        return user

    @staticmethod
    def _change_url(user) -> str:
        return reverse("admin:accounts_user_change", args=[user.pk])

    def _page_context(self, request, user, title):
        return {
            **self.admin_site.each_context(request),
            "title": title,
            "subtitle": str(user),
            "opts": self.model._meta,
            "original": user,
        }

    def _confirm_page(self, request, user, question, confirm_label, danger=False):
        if not self.has_manage_account_permission(request, user.pk):
            raise PermissionDenied
        context = {
            **self._page_context(request, user, confirm_label),
            "question": question,
            "confirm_label": confirm_label,
            "danger": danger,
            "cancel_url": self._change_url(user),
        }
        return TemplateResponse(request, "dashboard/confirm_action.html", context)

    def _temporary_password_page(self, request, user, result, intro):
        context = {
            **self._page_context(request, user, _("Temporary password")),
            "intro": intro,
            "user_dto": result.user,
            "temporary_password": result.temporary_password,
            "done_url": self._change_url(user),
        }
        # Admin views are never cached (Cache-Control: no-store), so the password is not kept.
        return TemplateResponse(request, "dashboard/temporary_password.html", context)

    def _back_with_error(self, request, user, error):
        self.message_user(request, localized_message(error), messages.ERROR)
        return HttpResponseRedirect(self._change_url(user))


@admin.register(Role)
class RoleAdmin(ReadOnlyForManagement, DashboardModelAdmin):
    """The six roles, read-only: they are fixed by the system (design section 8)."""

    list_display = ("name_ar", "name_en", "code", "users")
    fields = ("code", "name_ar", "name_en")
    readonly_fields = fields

    def get_queryset(self, request):
        return Role.objects.annotate(
            active_users=Count(
                "user_roles",
                filter=Q(user_roles__is_active=True, user_roles__user__is_active=True),
            )
        )

    @display(description=_("Users"))
    def users(self, obj):
        return obj.active_users

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


register_screen(Group.HOME, url_name="admin:index", title=_("Home"), icon="home")
register_screen(Group.USERS, model=User, title=_("Users"), icon="person")
register_screen(Group.USERS, model=Role, title=_("Roles"), icon="badge")
# The audit log viewer is core's screen (core/admin.py); core cannot import accounts, so the
# screen is placed in the Users group here.
register_screen(Group.USERS, model="core.AuditLog", title=_("Audit log"), icon="history")
