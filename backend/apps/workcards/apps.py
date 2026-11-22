from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WorkcardsConfig(AppConfig):
    name = "apps.workcards"
    label = "workcards"
    verbose_name = _("Work cards")
