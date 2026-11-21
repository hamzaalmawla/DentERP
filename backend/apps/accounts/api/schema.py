"""OpenAPI description of the API authentication (drf-spectacular)."""

from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class AccountJWTScheme(SimpleJWTScheme):
    target_class = "apps.accounts.api.authentication.AccountJWTAuthentication"
    name = "jwtAuth"

    def get_security_definition(self, auto_schema):
        definition = super().get_security_definition(auto_schema)
        definition["description"] = (
            "Access token from POST /api/v1/auth/login/. A user with several roles also sends "
            "the role in use in the X-Active-Role header."
        )
        return definition
