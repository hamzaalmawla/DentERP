"""Dashboard screens for core: the read-only audit log viewer (DB-17).

Who may open it is decided by the dashboard's role map (the accounts module places it in the
Users group, for the system administrator).
"""

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    DropdownFilter,
    RangeDateFilter,
)
from unfold.utils import parse_date_str

from apps.core.dashboard import DashboardModelAdmin

from .models import AuditLog


class _DistinctValuesFilter(DropdownFilter):
    """A dropdown of the values a column holds in the audit log."""

    field: str = ""

    def lookups(self, request, model_admin):
        values = (
            AuditLog.objects.exclude(**{self.field: ""})
            .order_by(self.field)
            .values_list(self.field, flat=True)
            .distinct()
        )
        return [(value, value) for value in values]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(**{self.field: self.value()})
        return queryset


class DayRangeFilter(RangeDateFilter):
    """From and to dates, both days included, in the clinic's time zone. (Unfold's filter
    compares a date-time column with midnight, which leaves out the "to" day.)"""

    def queryset(self, request, queryset):
        filters = {}
        for suffix, lookup in (("_from", "__date__gte"), ("_to", "__date__lte")):
            value = self.used_parameters.get(f"{self.parameter_name}{suffix}")
            if isinstance(value, str) and value:
                day = parse_date_str(value)
                if day is None:
                    return queryset.none()
                filters[f"{self.parameter_name}{lookup}"] = day
        return queryset.filter(**filters)


class ActionFilter(_DistinctValuesFilter):
    title = _("action")
    parameter_name = "action"
    field = "action"


class RecordTypeFilter(_DistinctValuesFilter):
    title = _("record type")
    parameter_name = "model"
    field = "model"


@admin.register(AuditLog)
class AuditLogAdmin(DashboardModelAdmin):
    list_display = ("at", "user", "action", "model", "object_id", "ip")
    list_filter = (
        ("user", AutocompleteSelectFilter),
        RecordTypeFilter,
        ActionFilter,
        ("at", DayRangeFilter),
    )
    list_filter_submit = True
    search_fields = ("object_id",)
    date_hierarchy = None
    list_select_related = ("user",)
    fields = ("at", "user", "action", "model", "object_id", "ip", "changes_display")
    readonly_fields = fields

    def get_search_results(self, request, queryset, search_term):
        # Exact record id: the column is text, but a partial match is never wanted.
        if search_term:
            return queryset.filter(object_id=search_term.strip()), False
        return queryset, False

    @admin.display(description=_("changes"))
    def changes_display(self, obj):
        text = json.dumps(obj.changes, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        return format_html('<pre dir="ltr" class="whitespace-pre-wrap">{}</pre>', text)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
