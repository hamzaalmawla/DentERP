"""Serializer pieces shared by every module's API."""

from datetime import UTC

from django.db import models
from rest_framework import serializers


class UTCDateTimeField(serializers.DateTimeField):
    """Date-times go out in UTC (ISO 8601); the app shows them in Damascus time."""

    def default_timezone(self):
        return UTC


class BaseModelSerializer(serializers.ModelSerializer):
    """Base for model serializers: date-times in UTC."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        models.DateTimeField: UTCDateTimeField,
    }


class ErrorSerializer(serializers.Serializer):
    """The error body every endpoint returns; reference it in ``extend_schema(responses=…)``."""

    code = serializers.CharField(help_text="Stable error code, for example step_out_of_order.")
    message = serializers.CharField(help_text="Message in the request's language.")
    details = serializers.DictField(help_text="Extra data, such as the invalid fields.")
