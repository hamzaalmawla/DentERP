from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AcademicsConfig(AppConfig):
    name = "apps.academics"
    label = "academics"
    verbose_name = _("Academics")
