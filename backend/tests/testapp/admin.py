"""A dashboard screen used only by the dashboard tests: notes, in the Patients group (seen by
super admin, management and reception). It leaves out ReadOnlyForManagement on purpose, to test
that the site adds it."""

from django.contrib import admin

from apps.accounts.dashboard import Group, register_screen
from apps.core.dashboard import DashboardModelAdmin

from .models import Note


@admin.register(Note)
class NoteAdmin(DashboardModelAdmin):
    list_display = ("title",)
    fields = ("title", "body")


register_screen(Group.PATIENTS, model=Note, title="Notes", icon="note")
