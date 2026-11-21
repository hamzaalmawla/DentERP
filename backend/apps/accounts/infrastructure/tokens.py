"""Adapter of the ``TokenIssuer`` port over djangorestframework-simplejwt.

Lifetimes and rotation are in ``settings.SIMPLE_JWT``. Refresh tokens are recorded in the
``token_blacklist`` tables, which is how rotation, logout and "revoke all" work.
"""

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.application.dtos import TokenPair
from apps.accounts.domain.errors import InvalidTokenError


class SimpleJwtTokenIssuer:
    def issue(self, user_id: int) -> TokenPair:
        user = get_user_model().all_objects.get(pk=user_id)
        refresh = RefreshToken.for_user(user)
        return TokenPair(access=str(refresh.access_token), refresh=str(refresh))

    def user_of(self, refresh: str) -> int:
        return self._user_id(self._valid(refresh))

    def rotate(self, refresh: str) -> TokenPair:
        token = self._valid(refresh)
        user_id = self._user_id(token)
        # Lock the row, so two requests with the same refresh token cannot both rotate it.
        outstanding = (
            OutstandingToken.objects.select_for_update()
            .filter(jti=token[api_settings.JTI_CLAIM])
            .first()
        )
        if outstanding is None or BlacklistedToken.objects.filter(token=outstanding).exists():
            raise InvalidTokenError()
        BlacklistedToken.objects.create(token=outstanding)
        return self.issue(user_id)

    def revoke(self, refresh: str) -> int:
        token = self._valid(refresh)
        token.blacklist()
        return self._user_id(token)

    def revoke_all(self, user_id: int) -> None:
        open_tokens = OutstandingToken.objects.filter(user_id=user_id).exclude(
            blacklistedtoken__isnull=False
        )
        BlacklistedToken.objects.bulk_create(
            [BlacklistedToken(token=token) for token in open_tokens], ignore_conflicts=True
        )

    @staticmethod
    def _valid(refresh: str) -> RefreshToken:
        try:
            return RefreshToken(refresh)
        except TokenError:
            raise InvalidTokenError() from None

    @staticmethod
    def _user_id(token: RefreshToken) -> int:
        try:
            return int(token[api_settings.USER_ID_CLAIM])
        except (KeyError, TypeError, ValueError):
            raise InvalidTokenError() from None
