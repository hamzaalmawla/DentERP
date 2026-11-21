"""Request and response bodies of the accounts endpoints. Responses are built from DTOs."""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.domain.devices import MAX_TOKEN_LENGTH, DevicePlatform
from apps.accounts.domain.roles import RoleCode
from apps.core.api.serializers import UTCDateTimeField

# One enum each in the OpenAPI schema (SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
ROLE_CHOICES = [role.value for role in RoleCode]
PLATFORM_CHOICES = [platform.value for platform in DevicePlatform]


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(label=_("username"), max_length=150, trim_whitespace=True)
    password = serializers.CharField(
        label=_("password"), max_length=128, trim_whitespace=False, style={"input_type": "password"}
    )


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(help_text="Access token, valid for 15 minutes.")
    refresh = serializers.CharField(help_text="Refresh token, valid for 30 days; rotated on use.")


class LoginResponseSerializer(TokenPairSerializer):
    must_change_password = serializers.BooleanField(
        help_text="True when the password is temporary: the app must send the user to "
        "POST /me/password/ first."
    )
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=ROLE_CHOICES),
        help_text="The roles the user holds. With several, send the chosen one in X-Active-Role.",
    )


class RefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField(label=_("refresh token"))


class ProfileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    full_name_ar = serializers.CharField()
    full_name_en = serializers.CharField()
    phone = serializers.CharField()
    university_id = serializers.CharField(allow_null=True)
    roles = serializers.ListField(child=serializers.ChoiceField(choices=ROLE_CHOICES))
    active_role = serializers.ChoiceField(
        choices=ROLE_CHOICES,
        allow_null=True,
        help_text="The role in X-Active-Role, or the only role; null until a user with "
        "several roles chooses one.",
    )
    must_change_password = serializers.BooleanField()
    last_login = UTCDateTimeField(allow_null=True)


class ChangePasswordRequestSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        label=_("current password"), max_length=128, trim_whitespace=False
    )
    new_password = serializers.CharField(
        label=_("new password"), max_length=128, trim_whitespace=False
    )


class DeviceRequestSerializer(serializers.Serializer):
    platform = serializers.ChoiceField(label=_("platform"), choices=PLATFORM_CHOICES)
    token = serializers.CharField(label=_("push token"), max_length=MAX_TOKEN_LENGTH)


class DeviceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=PLATFORM_CHOICES)
    last_seen = UTCDateTimeField()
