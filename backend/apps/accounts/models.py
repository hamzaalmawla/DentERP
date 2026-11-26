"""Accounts persistence: users, roles and push devices (design section 6).

Part of the persistence adapter (design section 5): services never import this file.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.accounts.domain.accounts import normalize_username
from apps.accounts.domain.devices import DevicePlatform
from apps.accounts.domain.roles import RoleCode
from apps.core.models import BaseModel, SoftDeleteQuerySet

ROLE_CHOICES = [
    (RoleCode.SUPER_ADMIN.value, _("System administrator")),
    (RoleCode.MANAGEMENT.value, _("Management")),
    (RoleCode.RECEPTION.value, _("Reception")),
    (RoleCode.SUPERVISOR.value, _("Supervisor")),
    (RoleCode.STUDENT.value, _("Student")),
    (RoleCode.TECHNICIAN.value, _("Maintenance technician")),
]

PLATFORM_CHOICES = [
    (DevicePlatform.ANDROID.value, "Android"),
    (DevicePlatform.IOS.value, "iOS"),
]


class UserManager(BaseUserManager.from_queryset(SoftDeleteQuerySet)):
    """The default manager: active users only, like every ``BaseModel`` manager.

    ``create_user`` and ``create_superuser`` serve Django's own commands and tests; the system
    creates users through the ``CreateUser`` service.
    """

    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

    def get_by_natural_key(self, username):
        return self.get(username=self.model.normalize_username(username))

    def create_user(self, username, password=None, **fields):
        user = self.model(username=self.model.normalize_username(username), **fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **fields):
        """A Django superuser who also holds the ``super_admin`` role."""
        fields.setdefault("is_superuser", True)
        user = self.create_user(username, password, **fields)
        role = Role.objects.filter(code=RoleCode.SUPER_ADMIN).first()
        if role is not None:
            UserRole.objects.get_or_create(user=user, role=role)
        return user


class AllUsersManager(BaseUserManager.from_queryset(SoftDeleteQuerySet)):
    """Every user, deactivated ones included."""


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    """A person who logs in: student, supervisor, technician, reception, management or the
    system administrator. What they may do comes from their roles (``UserRole``)."""

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
        error_messages={"unique": _("This username is already used.")},
    )
    full_name_ar = models.CharField(_("full name (Arabic)"), max_length=150)
    full_name_en = models.CharField(_("full name (English)"), max_length=150, blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    # NULL, not "", for users without one, so the unique constraint ignores them.
    university_id = models.CharField(  # noqa: DJ001
        _("university ID"), max_length=30, null=True, blank=True
    )
    # Setup owns departments; the user refers to the table by name only (DB-02).
    department = models.ForeignKey(
        "setup.Department",
        verbose_name=_("department"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    must_change_password = models.BooleanField(_("must change password"), default=False)
    failed_logins = models.PositiveSmallIntegerField(_("failed logins"), default=0)
    locked_until = models.DateTimeField(_("locked until"), null=True, blank=True)

    objects = UserManager()
    all_objects = AllUsersManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name_ar"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        default_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(
                fields=["university_id"],
                condition=Q(university_id__isnull=False),
                name="accounts_user_university_id_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.full_name_ar or self.username

    @classmethod
    def normalize_username(cls, username: str) -> str:
        return normalize_username(super().normalize_username(username))

    def clean(self) -> None:
        super().clean()
        if not self.university_id:
            self.university_id = None

    def get_full_name(self) -> str:
        return self.full_name_ar

    def get_short_name(self) -> str:
        return self.username


class Role(BaseModel):
    """One of the six roles (``domain.roles.RoleCode``), loaded by a data migration."""

    code = models.CharField(_("code"), max_length=30, unique=True, choices=ROLE_CHOICES)
    name_ar = models.CharField(_("name (Arabic)"), max_length=100)
    name_en = models.CharField(_("name (English)"), max_length=100)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name_ar


class UserRole(BaseModel):
    """A role a user holds. Removing a role deactivates the row; giving it back reactivates
    the same row."""

    user = models.ForeignKey(
        User, verbose_name=_("user"), on_delete=models.PROTECT, related_name="user_roles"
    )
    role = models.ForeignKey(
        Role, verbose_name=_("role"), on_delete=models.PROTECT, related_name="user_roles"
    )

    class Meta:
        verbose_name = _("user role")
        verbose_name_plural = _("user roles")
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="accounts_userrole_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.role}"


class DeviceToken(BaseModel):
    """A phone's push notification token (SYS-03)."""

    user = models.ForeignKey(
        User, verbose_name=_("user"), on_delete=models.PROTECT, related_name="device_tokens"
    )
    platform = models.CharField(_("platform"), max_length=10, choices=PLATFORM_CHOICES)
    token = models.CharField(_("token"), max_length=512, unique=True)
    last_seen = models.DateTimeField(_("last seen"))

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")

    def __str__(self) -> str:
        return f"{self.user} ({self.platform})"
