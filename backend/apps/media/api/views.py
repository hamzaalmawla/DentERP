"""Media endpoints (design section 7). Placeholders until P1.5 builds them (501)."""

from apps.accounts.api.permissions import HasAnyRole, RoleCode
from apps.core.api.placeholders import Planned, planned_view

Uploaders = HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR, RoleCode.TECHNICIAN)

MediaUploadView = planned_view(
    "media",
    prompt="P1.5",
    post=Planned(Uploaders, "Upload a photo or X-ray (multipart, Idempotency-Key header)"),
)

MediaDetailView = planned_view(
    "media",
    prompt="P1.5",
    get=Planned(Uploaders, "Signed links to a file and its thumbnail (valid 10 minutes)"),
)
