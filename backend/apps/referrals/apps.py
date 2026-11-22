from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReferralsConfig(AppConfig):
    name = "apps.referrals"
    label = "referrals"
    verbose_name = _("Referrals")
