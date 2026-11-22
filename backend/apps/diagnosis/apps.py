from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DiagnosisConfig(AppConfig):
    name = "apps.diagnosis"
    label = "diagnosis"
    verbose_name = _("Diagnosis")
