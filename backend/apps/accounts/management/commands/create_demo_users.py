"""``python manage.py create_demo_users``: one user per role, for development.

Creates ``demo_super_admin``, ``demo_management``, ``demo_reception``, ``demo_supervisor``,
``demo_student`` and ``demo_technician`` with the same password. Users that already exist are
left as they are. Refuses to run unless ``DEMO_USERS_ALLOWED`` is on (development only).
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts import container
from apps.core.infrastructure.request_context import acting_as

DEFAULT_PASSWORD = "Spu-Demo-2026"


class Command(BaseCommand):
    help = "Create one demo user per role (development only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password of every demo user (default: {DEFAULT_PASSWORD}).",
        )

    def handle(self, *args, password: str, **options):
        if not settings.DEMO_USERS_ALLOWED:
            raise CommandError("Demo users are for development only (DEMO_USERS_ALLOWED is off).")
        with acting_as(None):
            created = container.create_demo_users().execute(password)
        for user in created:
            self.stdout.write(f"Created {user.username} ({user.role})")
        if created:
            self.stdout.write(self.style.SUCCESS(f"Password for every demo user: {password}"))
        else:
            self.stdout.write("Every demo user already exists; nothing changed.")
