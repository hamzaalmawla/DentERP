from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    label = "accounts"
    verbose_name = _("Accounts")

    def ready(self) -> None:
        from .api import schema  # noqa: F401 — registers the OpenAPI auth scheme
