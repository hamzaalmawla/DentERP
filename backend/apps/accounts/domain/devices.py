"""Push notification devices (SYS-03): what a registered device must look like."""

from enum import StrEnum

from .errors import InvalidDeviceError

MAX_TOKEN_LENGTH = 512


class DevicePlatform(StrEnum):
    ANDROID = "android"
    IOS = "ios"


def validate_device(platform: str, token: str) -> tuple[DevicePlatform, str]:
    token = token.strip()
    if platform not in DevicePlatform or not token:
        raise InvalidDeviceError()
    if len(token) > MAX_TOKEN_LENGTH:
        raise InvalidDeviceError()
    return DevicePlatform(platform), token
