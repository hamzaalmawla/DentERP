"""One error format for every API error, in the request's language (design section 7)."""

import pytest
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework.test import APIClient

from apps.core.api.errors import exception_handler
from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.testapp.urls")]


def get(client, path, language):
    return client.get(path, HTTP_ACCEPT_LANGUAGE=language)


class TestDomainError:
    def test_arabic(self, api):
        response = get(api, "/api/v1/test/domain-error/", "ar")

        assert response.status_code == 400
        assert response.json() == {
            "code": "delete_not_allowed",
            "message": "لا يمكن حذف السجلات. عطّل السجل بدلاً من ذلك.",
            "details": {},
        }

    def test_english(self, api):
        response = get(api, "/api/v1/test/domain-error/", "en")

        assert response.status_code == 400
        assert response.json() == {
            "code": "delete_not_allowed",
            "message": "Records cannot be deleted. Deactivate the record instead.",
            "details": {},
        }

    def test_arabic_is_the_default_language(self, api):
        response = api.get("/api/v1/test/domain-error/")

        assert response.json()["message"] == "لا يمكن حذف السجلات. عطّل السجل بدلاً من ذلك."

    def test_placeholders_filled_from_details(self, api):
        response = get(api, "/api/v1/test/domain-error-params/", "en")

        assert response.json() == {
            "code": "too_many",
            "message": "At most 3 chairs.",
            "details": {"limit": 3},
        }

    def test_conflict_is_409(self, api):
        response = get(api, "/api/v1/test/conflict/", "en")

        assert response.status_code == 409
        assert response.json()["code"] == "already_approved"

    def test_error_carries_code_message_details(self):
        error = DomainError("x", _("Message."), {"a": 1})

        assert (error.code, error.message, error.details) == ("x", "Message.", {"a": 1})

    def test_not_found_error_defaults(self):
        assert NotFoundError().code == "not_found"


class TestValidation:
    def test_arabic(self, api):
        response = api.post(
            "/api/v1/test/validation/", {}, format="json", HTTP_ACCEPT_LANGUAGE="ar"
        )

        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert body["message"] == "البيانات المرسلة غير صالحة."
        assert body["details"] == {"name": ["هذا الحقل مطلوب."]}

    def test_english(self, api):
        response = api.post(
            "/api/v1/test/validation/",
            {"name": "too long"},
            format="json",
            HTTP_ACCEPT_LANGUAGE="en",
        )

        assert response.json() == {
            "code": "validation_error",
            "message": "The data sent is not valid.",
            "details": {"name": ["Ensure this field has no more than 5 characters."]},
        }

    def test_django_validation_error(self, api):
        response = get(api, "/api/v1/test/django-validation/", "en")

        assert response.status_code == 400
        assert response.json() == {
            "code": "validation_error",
            "message": "The data sent is not valid.",
            "details": {"due": ["Bad date."]},
        }

    def test_malformed_json(self, api):
        response = api.post(
            "/api/v1/test/validation/",
            "{not json",
            content_type="application/json",
            HTTP_ACCEPT_LANGUAGE="en",
        )

        assert response.status_code == 400
        assert response.json()["code"] == "parse_error"


class TestNotFound:
    def test_arabic(self, api):
        response = get(api, "/api/v1/test/not-found/", "ar")

        assert response.status_code == 404
        assert response.json() == {
            "code": "not_found",
            "message": "السجل غير موجود.",
            "details": {},
        }

    def test_english_never_names_the_model(self, api):
        response = get(api, "/api/v1/test/not-found/", "en")

        assert response.json() == {
            "code": "not_found",
            "message": "The record was not found.",
            "details": {},
        }


class TestPermissionDenied:
    def test_arabic(self, api):
        response = get(api, "/api/v1/test/permission-denied/", "ar")

        assert response.status_code == 403
        assert response.json() == {
            "code": "permission_denied",
            "message": "ليس لديك صلاحية للقيام بهذا الإجراء.",
            "details": {},
        }

    def test_english(self, api):
        response = get(api, "/api/v1/test/permission-denied/", "en")

        assert response.status_code == 403
        assert response.json() == {
            "code": "permission_denied",
            "message": "You do not have permission to perform this action.",
            "details": {},
        }


class TestOtherApiErrors:
    def test_not_logged_in(self):
        response = get(APIClient(), "/api/v1/test/domain-error/", "en")

        assert response.status_code == 403  # session auth; JWT (P0.3) makes this 401
        assert response.json() == {
            "code": "not_authenticated",
            "message": "Authentication credentials were not provided.",
            "details": {},
        }

    def test_method_not_allowed(self, api):
        response = api.delete("/api/v1/test/domain-error/", HTTP_ACCEPT_LANGUAGE="en")

        assert response.status_code == 405
        assert response.json()["code"] == "method_not_allowed"

    def test_responses_are_json(self, api):
        response = get(api, "/api/v1/test/not-found/", "en")

        assert response["Content-Type"] == "application/json"


class TestHandlerDirectly:
    """Paths the accounts module (P0.3) relies on: token errors and throttling."""

    def test_token_error_with_a_detail_dict(self):
        exc = AuthenticationFailed(
            {"detail": "Token is invalid", "code": "token_not_valid", "messages": []}
        )

        response = exception_handler(exc, {})

        assert response.status_code == 401
        assert response.data == {
            "code": "token_not_valid",
            "message": "Token is invalid",
            "details": {"messages": []},
        }

    def test_throttled_gives_the_wait_and_retry_after(self):
        response = exception_handler(Throttled(wait=42), {})

        assert response.status_code == 429
        assert response.data["code"] == "throttled"
        assert response.data["details"] == {"wait": 42}
        assert response["Retry-After"] == "42"

    def test_unexpected_errors_are_left_to_django(self):
        assert exception_handler(ZeroDivisionError(), {}) is None
