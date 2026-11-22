from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SchedulingConfig(AppConfig):
    name = "apps.scheduling"
    label = "scheduling"
    verbose_name = _("Scheduling")
