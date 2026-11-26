"""ORM adapters of the accounts repository ports."""

from collections.abc import Iterable
from datetime import datetime

from django.db.models import Prefetch

from apps.accounts.application.dtos import (
    AuthContext,
    DeviceDTO,
    NewAccount,
    UserDetails,
    UserDTO,
)
from apps.accounts.domain.accounts import Account
from apps.accounts.models import DeviceToken, Role, User, UserRole


def _account(user: User) -> Account:
    return Account(
        id=user.pk,
        username=user.username,
        password_hash=user.password,
        must_change_password=user.must_change_password,
        failed_logins=user.failed_logins,
        locked_until=user.locked_until,
        last_login=user.last_login,
        full_name_ar=user.full_name_ar,
        full_name_en=user.full_name_en,
        university_id=user.university_id,
    )


def _active_roles(user_id: int) -> frozenset[str]:
    return frozenset(
        UserRole.objects.filter(user_id=user_id, role__is_active=True).values_list(
            "role__code", flat=True
        )
    )


class OrmAccountRepository:
    def get(self, user_id: int, *, for_update: bool = False) -> Account | None:
        user = self._users(for_update).filter(pk=user_id).first()
        return _account(user) if user else None

    def get_by_username(self, username: str, *, for_update: bool = False) -> Account | None:
        user = self._users(for_update).filter(username=username).first()
        return _account(user) if user else None

    def save(self, account: Account) -> None:
        user = User.objects.get(pk=account.id)
        user.password = account.password_hash
        user.must_change_password = account.must_change_password
        user.failed_logins = account.failed_logins
        user.locked_until = account.locked_until
        user.last_login = account.last_login
        user.save(
            update_fields=[
                "password",
                "must_change_password",
                "failed_logins",
                "locked_until",
                "last_login",
            ]
        )

    def create(self, account: NewAccount) -> int:
        user = User(
            username=account.username,
            full_name_ar=account.full_name_ar,
            full_name_en=account.full_name_en,
            phone=account.phone,
            university_id=account.university_id,
            department_id=account.department_id,
            password=account.password_hash,
            must_change_password=account.must_change_password,
        )
        user.save()
        self.set_roles(user.pk, account.roles)
        return user.pk

    def username_exists(self, username: str) -> bool:
        return User.all_objects.filter(username=username).exists()

    def university_id_exists(
        self, university_id: str, *, exclude_user_id: int | None = None
    ) -> bool:
        users = User.all_objects.filter(university_id=university_id)
        if exclude_user_id is not None:
            users = users.exclude(pk=exclude_user_id)
        return users.exists()

    def details_of(self, user_id: int) -> UserDetails | None:
        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return None
        return UserDetails(
            full_name_ar=user.full_name_ar,
            full_name_en=user.full_name_en,
            phone=user.phone,
            university_id=user.university_id,
            department_id=user.department_id,
        )

    def update_details(self, user_id: int, details: UserDetails) -> None:
        user = User.objects.get(pk=user_id)
        user.full_name_ar = details.full_name_ar
        user.full_name_en = details.full_name_en
        user.phone = details.phone
        user.university_id = details.university_id
        user.department_id = details.department_id
        user.save(
            update_fields=["full_name_ar", "full_name_en", "phone", "university_id", "department"]
        )

    def deactivate(self, user_id: int) -> None:
        User.objects.get(pk=user_id).deactivate()

    def roles_of(self, user_id: int) -> frozenset[str]:
        return _active_roles(user_id)

    def set_roles(self, user_id: int, roles: Iterable[str]) -> None:
        wanted = frozenset(roles)
        rows = {
            row.role.code: row
            for row in UserRole.all_objects.filter(user_id=user_id).select_related("role")
        }
        for code, row in rows.items():
            if code not in wanted and row.is_active:
                row.deactivate()
            elif code in wanted and not row.is_active:
                row.activate()
        for role in Role.objects.filter(code__in=wanted - rows.keys()):
            UserRole.objects.create(user_id=user_id, role=role)

    def to_dto(self, user_id: int) -> UserDTO | None:
        user = (
            User.objects.filter(pk=user_id)
            .prefetch_related(
                Prefetch(
                    "user_roles",
                    queryset=UserRole.objects.filter(role__is_active=True).select_related("role"),
                    to_attr="active_user_roles",
                )
            )
            .first()
        )
        if user is None:
            return None
        return UserDTO(
            id=user.pk,
            username=user.username,
            full_name_ar=user.full_name_ar,
            full_name_en=user.full_name_en,
            phone=user.phone,
            university_id=user.university_id,
            roles=tuple(sorted(row.role.code for row in user.active_user_roles)),
            must_change_password=user.must_change_password,
            locked_until=user.locked_until,
            last_login=user.last_login,
            department_id=user.department_id,
        )

    @staticmethod
    def _users(for_update: bool):
        return User.objects.select_for_update() if for_update else User.objects.all()


class OrmRoleRepository:
    def active_codes(self) -> frozenset[str]:
        return frozenset(Role.objects.values_list("code", flat=True))


class OrmAuthContextReader:
    def auth_context(self, user_id: int) -> AuthContext | None:
        must_change = (
            User.objects.filter(pk=user_id).values_list("must_change_password", flat=True).first()
        )
        if must_change is None:
            return None
        return AuthContext(
            user_id=user_id, roles=_active_roles(user_id), must_change_password=must_change
        )


class OrmDeviceTokenRepository:
    def register(self, user_id: int, platform: str, token: str, seen_at: datetime) -> DeviceDTO:
        device = DeviceToken.all_objects.select_for_update().filter(token=token).first()
        if device is None:
            device = DeviceToken.objects.create(
                user_id=user_id, platform=platform, token=token, last_seen=seen_at
            )
        else:
            device.user_id = user_id
            device.platform = platform
            device.last_seen = seen_at
            device.is_active = True
            device.save(update_fields=["user", "platform", "last_seen", "is_active"])
        return DeviceDTO(id=device.pk, platform=device.platform, last_seen=device.last_seen)
