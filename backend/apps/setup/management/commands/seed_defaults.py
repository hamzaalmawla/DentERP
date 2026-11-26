"""``python manage.py seed_defaults``: the default lists and the Release 1 setup data.

Loads ``apps/setup/seed/defaults.json``: tooth codes, medical history items, soft tissue sites,
the index set, the chair checklist, fault categories, round times and the other system
settings (SRS section 4), then the two departments, the diagnosis clinic and the Endodontics
clinic with their chairs, the sessions, a current term and the Endodontics case and treatment
types (docs/build-prompts.md section 1). Safe to run again: records already there are left as
they are, so changes made in the dashboard are kept.
"""

from django.core.management.base import BaseCommand

from apps.core.infrastructure.request_context import acting_as
from apps.setup import container


class Command(BaseCommand):
    help = "Load the default setup data (safe to run again)."

    def handle(self, *args, **options):
        with acting_as(None):
            report = container.seed_defaults().execute()
        for table in sorted(report.created.keys() | report.existing.keys()):
            created, existing = report.created.get(table, 0), report.existing.get(table, 0)
            self.stdout.write(f"{table}: {created} created, {existing} already there")
        if any(report.created.values()):
            self.stdout.write(self.style.SUCCESS("Default setup data loaded."))
        else:
            self.stdout.write("Every default record already exists; nothing changed.")
