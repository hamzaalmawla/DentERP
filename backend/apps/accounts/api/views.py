"""Auth and "me" endpoints (design section 7). Each view validates the body, calls one
service and serializes the DTO it returns."""

from dataclasses import asdict

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import container
from apps.accounts.application.services import (
    ChangePasswordCommand,
    LoginCommand,
    RegisterDeviceCommand,
)
from apps.core.api.serializers import ErrorSerializer

from .context import request_auth
from .serializers import (
    ChangePasswordRequestSerializer,
    DeviceRequestSerializer,
    DeviceSerializer,
    LoginRequestSerializer,
    LoginResponseSerializer,
    ProfileSerializer,
    RefreshRequestSerializer,
    TokenPairSerializer,
)
from .throttles import LoginRateThrottle

ERRORS = {400: ErrorSerializer, 401: ErrorSerializer, 403: ErrorSerializer}


def _valid(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        tags=["auth"],
        summary="Log in with username and password",
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer, **ERRORS, 429: ErrorSerializer},
        auth=[],
        description="Errors: invalid_credentials (400), account_locked (403, details."
        "locked_until), no_role (403). Five failed logins lock the account for 15 minutes.",
    )
    def post(self, request):
        data = _valid(LoginRequestSerializer, request)
        result = container.login().execute(LoginCommand(data["username"], data["password"]))
        return Response(LoginResponseSerializer(asdict(result)).data)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        summary="Get a new token pair",
        request=RefreshRequestSerializer,
        responses={200: TokenPairSerializer, 400: ErrorSerializer},
        auth=[],
        description="The refresh token is rotated: the one sent can no longer be used. "
        "Error: token_invalid (400) — log in again.",
    )
    def post(self, request):
        data = _valid(RefreshRequestSerializer, request)
        tokens = container.refresh_token().execute(data["refresh"])
        return Response(TokenPairSerializer(asdict(tokens)).data)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        summary="Log out",
        request=RefreshRequestSerializer,
        responses={204: OpenApiResponse(description="Logged out."), 400: ErrorSerializer},
        auth=[],
        description="Revokes the refresh token. Error: token_invalid (400).",
    )
    def post(self, request):
        data = _valid(RefreshRequestSerializer, request)
        container.logout().execute(data["refresh"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    password_change_allowed = True

    @extend_schema(
        tags=["me"],
        summary="My profile and roles",
        responses={200: ProfileSerializer, 401: ErrorSerializer, 403: ErrorSerializer},
    )
    def get(self, request):
        auth = request_auth(request)
        profile = container.get_profile().execute(request.user.pk)
        return Response(
            ProfileSerializer({**asdict(profile), "active_role": auth.active_role}).data
        )


class MyPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    password_change_allowed = True

    @extend_schema(
        tags=["me"],
        summary="Change my password",
        request=ChangePasswordRequestSerializer,
        responses={200: TokenPairSerializer, **ERRORS},
        description="Also ends the first-login gate. Every token issued before is revoked; "
        "use the new pair returned. Errors: wrong_password, password_unchanged, "
        "password_invalid (details.messages).",
    )
    def post(self, request):
        data = _valid(ChangePasswordRequestSerializer, request)
        tokens = container.change_password().execute(
            ChangePasswordCommand(
                user_id=request.user.pk,
                current_password=data["current_password"],
                new_password=data["new_password"],
            )
        )
        return Response(TokenPairSerializer(asdict(tokens)).data)


class MyDevicesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["me"],
        summary="Register this phone for push notifications",
        request=DeviceRequestSerializer,
        responses={201: DeviceSerializer, **ERRORS},
    )
    def post(self, request):
        data = _valid(DeviceRequestSerializer, request)
        device = container.register_device().execute(
            RegisterDeviceCommand(
                user_id=request.user.pk, platform=data["platform"], token=data["token"]
            )
        )
        return Response(DeviceSerializer(asdict(device)).data, status=status.HTTP_201_CREATED)
