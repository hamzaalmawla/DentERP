"""Helpers for API tests that use real JWT tokens, for this module and the others.

response = login("demo_student", "Spu-Demo-2026")
client = bearer(response.json()["access"], role="student")
client.get("/api/v1/me/")
"""

from rest_framework.test import APIClient

LOGIN_URL = "/api/v1/auth/login/"


def login(username: str, password: str, client: APIClient | None = None, language: str = "en"):
    client = client or APIClient()
    return client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
        HTTP_ACCEPT_LANGUAGE=language,
    )


def bearer(access: str, role: str | None = None, language: str = "en") -> APIClient:
    """A client that sends the access token, and ``X-Active-Role`` when ``role`` is given."""
    client = APIClient(HTTP_ACCEPT_LANGUAGE=language)
    headers = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
    if role:
        headers["HTTP_X_ACTIVE_ROLE"] = role
    client.credentials(**headers)
    return client
