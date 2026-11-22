from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MediaConfig(AppConfig):
    name = "apps.media"
    label = "media"
    verbose_name = _("Media")
