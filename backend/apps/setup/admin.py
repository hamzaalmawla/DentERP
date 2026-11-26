"""Setup dashboard screens (DB-04, DB-06, DB-18): Facilities (departments, clinics with their
chairs, chairs, sessions, terms), Lists (sortable) and Settings (one page).

Every change goes through a setup service (``SaveRecord``, ``SetRecordActive``, ``Reorder``,
``AddChairs``, ``SetChairStatus``, ``UpdateSettings``); nothing here saves a model itself. The
forms call the services in ``clean()`` so each service error shows on its field. Only the
system administrator sees these groups (design section 11); the services check it again.
"""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Max, Q
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display
from unfold.widgets import (
    UnfoldAdminColorInputWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminTimeWidget,
    UnfoldBooleanSwitchWidget,
)

from apps.accounts.dashboard.navigation import Group, register_screen
from apps.core import container as core_container
from apps.core.api.errors import localized_message
from apps.core.dashboard import DashboardModelAdmin, DashboardTabularInline
from apps.core.domain.errors import DomainError

from . import container
from .application.dtos import SetChairStatusCommand
from .application.services import (
    AddChairsCommand,
    ReorderCommand,
    SaveRecordCommand,
    SetRecordActiveCommand,
)
from .domain.records import Table
from .domain.settings import LANGUAGES, SETTINGS, SettingType
from .domain.values import ChairStatus
from .models import (
    CHAIR_STATUS_CHOICES,
    CaseType,
    Chair,
    ChairStatusChange,
    ChecklistItem,
    Clinic,
    Department,
    FaultCategory,
    IndexDefinition,
    MedicalHistoryItem,
    Session,
    SoftTissueSite,
    SystemSetting,
    Term,
    ToothCode,
    TreatmentType,
)

FORM_PAGE = "setup/dashboard/form_page.html"


def show_service_error(form: forms.Form, error: DomainError) -> None:
    """Show ``error`` on the field it names (``details["field"]``; ``department_id`` is the
    form's ``department``), or above the form."""
    field = str(error.details.get("field", ""))
    for name in (field, field.removesuffix("_id")):
        if name and name in form.fields:
            form.add_error(name, localized_message(error))
            return
    form.add_error(None, localized_message(error))


# --- One screen per table -----------------------------------------------------------------


class RecordForm(forms.ModelForm):
    """A record's form. ``clean()`` hands the values to ``SaveRecord``; the model is never
    validated or saved by the form: the services hold the rules."""

    actor = None  # set by RecordAdmin.get_form, on a new class each time
    table: Table | None = None
    saved = None

    def _post_clean(self):
        pass

    def record_values(self) -> dict[str, Any]:
        """The cleaned values as the service names them: a related record by its id."""
        model_fields = {f.name: f for f in self._meta.model._meta.concrete_fields}
        values = {}
        for name, value in self.cleaned_data.items():
            field = model_fields.get(name)
            if field is None:
                continue  # a form-only field, such as a clinic's chairs to add
            if field.is_relation:
                values[field.attname] = value.pk if value is not None else None
            else:
                values[name] = value
        return values

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        record_id = self.instance.pk
        if record_id is not None:  # fields the form does not show keep their value
            stored = {
                f.attname: getattr(self.instance, f.attname)
                for f in self._meta.model._meta.concrete_fields
            }
        else:
            stored = {}
        try:
            with core_container.unit_of_work():  # the record and its follow-ups, or neither
                self.saved = container.save_record().execute(
                    self.actor,
                    SaveRecordCommand(self.table, {**stored, **self.record_values()}, record_id),
                )
                self.after_save(self.saved.id)
        except DomainError as error:
            show_service_error(self, error)
        return cleaned

    def after_save(self, record_id: int) -> None:
        """More service calls in the same unit of work (a clinic's new chairs)."""


class RecordAdmin(DashboardModelAdmin):
    """The screen of one configuration table. Deactivated records stay in the list (filter
    "active") and are read-only; they can be activated again."""

    table: Table
    form = RecordForm
    list_filter: tuple = ("is_active",)
    actions = ["deactivate_selected", "activate_selected"]
    list_per_page = 50

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def _changeform_view(self, request, object_id, form_url, extra_context):
        # Django runs this view in one transaction. The form's services save in clean(); when
        # the page is shown again with an error (in the form or anywhere else on the page),
        # undo what they saved.
        response = super()._changeform_view(request, object_id, form_url, extra_context)
        if request.method == "POST" and response.status_code == 200:
            transaction.set_rollback(True)
        return response

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        form.actor = self.actor(request)
        form.table = self.table
        return form

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or getattr(obj, "is_active", True)
        )

    # Saving: the form's service already did the work ----------------------------------

    def save_form(self, request, form, change):
        if isinstance(form, RecordForm):
            return self.model.all_objects.get(pk=form.saved.id)
        return form.instance  # a row of a sortable list: saved in save_model

    def save_model(self, request, obj, form, change):
        pass

    def save_related(self, request, form, formsets, change):
        pass  # the inlines are read-only

    def construct_change_message(self, request, form, formsets, add=False):
        return []  # Django's admin log is not written; the services audit every change

    # Columns and actions ------------------------------------------------------------

    @display(description=_("Status"), label={_("Active"): "success", _("Deactivated"): "danger"})
    def record_status(self, obj):
        return _("Active") if obj.is_active else _("Deactivated")

    def _set_active(self, request, queryset, active: bool) -> None:
        changed = 0
        for record_id in queryset.filter(is_active=not active).values_list("pk", flat=True):
            try:
                container.set_record_active().execute(
                    self.actor(request), SetRecordActiveCommand(self.table, record_id, active)
                )
                changed += 1
            except DomainError as error:
                self.message_user(request, localized_message(error), messages.ERROR)
        message = (
            _("Records activated: %(count)d.") if active else _("Records deactivated: %(count)d.")
        )
        self.message_user(request, message % {"count": changed}, messages.SUCCESS)

    @admin.action(description=_("Deactivate the selected records"), permissions=["change"])
    def deactivate_selected(self, request, queryset):
        self._set_active(request, queryset, False)

    @admin.action(description=_("Activate the selected records"), permissions=["change"])
    def activate_selected(self, request, queryset):
        self._set_active(request, queryset, True)


class OrderForm(forms.ModelForm):
    """The hidden order of one row of a sortable list (the list's drag and drop)."""

    def _post_clean(self):
        pass


class OrderedRecordAdmin(RecordAdmin):
    """A list the administrator orders by dragging its rows (design section 11, Lists)."""

    ordering_field = "order"
    hide_ordering_field = True

    def get_changelist_form(self, request, **kwargs):
        return forms.modelform_factory(self.model, form=OrderForm, fields=["order"])

    def get_changeform_initial_data(self, request):
        """A new item goes to the end of the list."""
        highest = self.model.all_objects.aggregate(n=Max("order"))["n"]
        return {"order": (highest or 0) + 1, **super().get_changeform_initial_data(request)}

    def save_model(self, request, obj, form, change):
        if isinstance(form, OrderForm):  # a row of the dragged list
            try:
                container.reorder().execute(
                    self.actor(request),
                    ReorderCommand(self.table, {obj.pk: form.cleaned_data["order"]}),
                )
            except DomainError as error:
                self.message_user(request, localized_message(error), messages.ERROR)


# --- Facilities ---------------------------------------------------------------------------


@admin.register(Term)
class TermAdmin(RecordAdmin):
    table = Table.TERM
    list_display = ("name", "start_date", "end_date", "is_current", "record_status")
    fields = ("name", "start_date", "end_date", "is_current")
    search_fields = ("name",)
    ordering = ("-start_date",)


@admin.register(Department)
class DepartmentAdmin(RecordAdmin):
    table = Table.DEPARTMENT
    list_display = ("name_ar", "name_en", "head", "record_status")
    fields = ("name_ar", "name_en", "head")
    search_fields = ("name_ar", "name_en")
    autocomplete_fields = ("head",)
    list_select_related = ("head",)


class ChairInline(DashboardTabularInline):
    """The clinic's chairs, read-only here; each opens the chair's own page."""

    model = Chair
    fields = ("number", "chair_status", "record_status")
    readonly_fields = fields
    show_change_link = True
    ordering = ("number",)
    verbose_name_plural = _("chairs")

    def get_queryset(self, request):
        return Chair.all_objects.all()

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @display(
        description=_("Chair status"),
        label={_("In service"): "success", _("Out of service"): "warning"},
    )
    def chair_status(self, obj):
        return obj.get_status_display()

    @display(description=_("Status"), label={_("Active"): "success", _("Deactivated"): "danger"})
    def record_status(self, obj):
        return _("Active") if obj.is_active else _("Deactivated")


class ClinicForm(RecordForm):
    chairs_to_add = forms.IntegerField(
        label=_("Chairs to add"),
        required=False,
        min_value=0,
        help_text=_("New chairs, in service, numbered after the clinic's highest chair."),
        widget=UnfoldAdminIntegerFieldWidget,
    )

    def after_save(self, record_id: int) -> None:
        count = self.cleaned_data.get("chairs_to_add")
        if count:
            container.add_chairs().execute(self.actor, AddChairsCommand(record_id, count))


@admin.register(Clinic)
class ClinicAdmin(RecordAdmin):
    table = Table.CLINIC
    form = ClinicForm
    list_display = ("number", "name_ar", "name_en", "type", "department", "chairs", "record_status")
    list_filter = ("type", "department", "is_active")
    fields = (
        "number",
        "name_ar",
        "name_en",
        "type",
        "department",
        "building",
        "floor",
        "chairs_to_add",
    )
    search_fields = ("number", "name_ar", "name_en")
    inlines = [ChairInline]
    list_select_related = ("department",)

    def get_queryset(self, request):
        active = Q(chairs__is_active=True)
        return Clinic.all_objects.annotate(
            active_chairs=Count("chairs", filter=active),
            chairs_in_service=Count(
                "chairs", filter=active & Q(chairs__status=ChairStatus.IN_SERVICE.value)
            ),
        )

    @display(description=_("Chairs in service"))
    def chairs(self, obj):
        return f"{obj.chairs_in_service} / {obj.active_chairs}"


class ChairStatusHistoryInline(DashboardTabularInline):
    model = ChairStatusChange
    fields = ("at", "from_status", "to_status", "reason", "by")
    readonly_fields = fields
    ordering = ("-at",)
    verbose_name_plural = _("status history")

    def get_queryset(self, request):
        return ChairStatusChange.all_objects.select_related("by")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ChairStatusForm(forms.Form):
    status = forms.ChoiceField(
        label=_("Status"), choices=CHAIR_STATUS_CHOICES, widget=UnfoldAdminSelectWidget
    )
    reason = forms.CharField(label=_("Reason"), widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}))


@admin.register(Chair)
class ChairAdmin(RecordAdmin):
    table = Table.CHAIR
    list_display = ("clinic", "number", "chair_status", "record_status")
    list_filter = ("clinic", "status", "is_active")
    list_select_related = ("clinic",)
    search_fields = ("clinic__number", "clinic__name_ar")
    ordering = ("clinic__number", "number")
    inlines = [ChairStatusHistoryInline]
    actions_detail = ["change_status_action"]

    def get_fields(self, request, obj=None):
        return ("clinic", "number", "status") if obj else ("clinic", "number")

    def get_readonly_fields(self, request, obj=None):
        # A chair stays in its clinic; its status changes with a reason (the button above).
        return ("clinic", "status") if obj else ()

    @display(
        description=_("Chair status"),
        label={_("In service"): "success", _("Out of service"): "warning"},
    )
    def chair_status(self, obj):
        return obj.get_status_display()

    def has_change_status_permission(self, request, object_id=None):
        if not self.has_change_permission(request):
            return False
        return object_id is None or Chair.objects.filter(pk=object_id).exists()

    @action(
        description=_("Put in or out of service"),
        url_path="status",
        icon="build",
        permissions=["change_status"],
    )
    def change_status_action(self, request, object_id):
        chair = Chair.objects.filter(pk=object_id).select_related("clinic").first()
        if chair is None:
            raise Http404
        change_url = reverse("admin:setup_chair_change", args=[chair.pk])
        form = ChairStatusForm(
            request.POST or None,
            initial={
                "status": ChairStatus.OUT_OF_SERVICE.value
                if chair.status == ChairStatus.IN_SERVICE.value
                else ChairStatus.IN_SERVICE.value
            },
        )
        if request.method == "POST" and form.is_valid():
            try:
                container.set_chair_status().execute(
                    SetChairStatusCommand(
                        chair.pk,
                        ChairStatus(form.cleaned_data["status"]),
                        form.cleaned_data["reason"],
                        self.actor(request).user_id,
                    )
                )
            except DomainError as error:
                show_service_error(form, error)
            else:
                self.message_user(request, _("The chair's status was saved."), messages.SUCCESS)
                return HttpResponseRedirect(change_url)
        return _form_page(
            self,
            request,
            form,
            title=_("Chair status"),
            subtitle=f"{chair.clinic} — {chair}",
            submit_label=_("Save"),
            cancel_url=change_url,
        )


@admin.register(Session)
class SessionAdmin(RecordAdmin):
    table = Table.SESSION
    list_display = (
        "name_ar",
        "name_en",
        "applies_to",
        "start_time",
        "end_time",
        "order",
        "record_status",
    )
    list_filter = ("clinic_type", "clinic", "is_active")
    fields = ("clinic_type", "clinic", "name_ar", "name_en", "start_time", "end_time", "order")
    ordering = ("clinic_type", "clinic__number", "order")
    list_select_related = ("clinic",)

    @display(description=_("For"))
    def applies_to(self, obj):
        return obj.clinic or obj.get_clinic_type_display()


# --- Lists ----------------------------------------------------------------------------------


@admin.register(CaseType)
class CaseTypeAdmin(OrderedRecordAdmin):
    table = Table.CASE_TYPE
    list_display = ("name_ar", "name_en", "kind", "record_status")
    list_filter = ("kind", "is_active")
    fields = ("name_ar", "name_en", "kind", "order")


class ToothCodeForm(RecordForm):
    class Meta:
        widgets = {"color": UnfoldAdminColorInputWidget}


@admin.register(ToothCode)
class ToothCodeAdmin(OrderedRecordAdmin):
    table = Table.TOOTH_CODE
    form = ToothCodeForm
    list_display = ("letter", "meaning_ar", "meaning_en", "colour", "record_status")
    fields = ("letter", "meaning_ar", "meaning_en", "color", "order")

    @display(description=_("colour"))
    def colour(self, obj):
        return format_html(
            '<span class="inline-block rounded-full" style="background:{};width:1.25rem;'
            'height:1.25rem" title="{}"></span>',
            obj.color,
            obj.color,
        )


@admin.register(MedicalHistoryItem)
class MedicalHistoryItemAdmin(OrderedRecordAdmin):
    table = Table.MEDICAL_HISTORY_ITEM
    list_display = ("question_ar", "question_en", "answer_type", "is_alert", "record_status")
    list_filter = ("answer_type", "is_alert", "is_active")
    fields = ("question_ar", "question_en", "answer_type", "is_alert", "order")


@admin.register(SoftTissueSite)
class SoftTissueSiteAdmin(OrderedRecordAdmin):
    table = Table.SOFT_TISSUE_SITE
    list_display = ("name_ar", "name_en", "record_status")
    fields = ("name_ar", "name_en", "order")


@admin.register(IndexDefinition)
class IndexDefinitionAdmin(OrderedRecordAdmin):
    table = Table.INDEX_DEFINITION
    list_display = ("kind", "tooth", "surface", "min_score", "max_score", "record_status")
    list_filter = ("kind", "is_active")
    fields = ("kind", "tooth", "surface", "min_score", "max_score", "order")


@admin.register(TreatmentType)
class TreatmentTypeAdmin(OrderedRecordAdmin):
    table = Table.TREATMENT_TYPE
    list_display = ("name_ar", "name_en", "department", "case_type", "record_status")
    list_filter = ("department", "is_active")
    fields = ("name_ar", "name_en", "department", "case_type", "order")
    list_select_related = ("department", "case_type")


@admin.register(ChecklistItem)
class ChecklistItemAdmin(OrderedRecordAdmin):
    table = Table.CHECKLIST_ITEM
    list_display = ("name_ar", "name_en", "record_status")
    fields = ("name_ar", "name_en", "order")


@admin.register(FaultCategory)
class FaultCategoryAdmin(OrderedRecordAdmin):
    table = Table.FAULT_CATEGORY
    list_display = ("name_ar", "name_en", "blocks_chair", "record_status")
    list_filter = ("blocks_chair", "is_active")
    fields = ("name_ar", "name_en", "blocks_chair", "order")


# --- Settings ---------------------------------------------------------------------------------

_LANGUAGE_NAMES = {"ar": _("Arabic"), "en": _("English")}


def _setting_field(definition) -> forms.Field:
    label = _(definition.label)
    match definition.type:
        case SettingType.TEXT:
            return forms.CharField(label=label, max_length=200, widget=UnfoldAdminTextInputWidget)
        case SettingType.LANGUAGE:
            return forms.ChoiceField(
                label=label,
                choices=[(code, _LANGUAGE_NAMES[code]) for code in LANGUAGES],
                widget=UnfoldAdminSelectWidget,
            )
        case SettingType.WHOLE_NUMBER:
            return forms.IntegerField(
                label=label,
                min_value=definition.minimum,
                max_value=definition.maximum,
                widget=UnfoldAdminIntegerFieldWidget,
            )
        case SettingType.SWITCH:
            return forms.BooleanField(label=label, required=False, widget=UnfoldBooleanSwitchWidget)
        case SettingType.TIME:
            return forms.TimeField(label=label, widget=UnfoldAdminTimeWidget)
    raise AssertionError(definition.type)  # pragma: no cover


class SystemSettingsForm(forms.Form):
    """Every system setting on one page (DB-18)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for definition in SETTINGS:
            self.fields[definition.key] = _setting_field(definition)


@admin.register(SystemSetting)
class SystemSettingAdmin(DashboardModelAdmin):
    """One page with every setting instead of a list of keys."""

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        name = f"{self.opts.app_label}_{self.opts.model_name}_changelist"
        return [path("", self.admin_site.admin_view(self.settings_view), name=name)]

    def settings_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        can_change = self.has_change_permission(request)
        stored = dict(SystemSetting.objects.values_list("key", "value"))
        form = SystemSettingsForm(
            request.POST if request.method == "POST" else None,
            initial={s.key: stored.get(s.key) for s in SETTINGS},
        )
        if request.method == "POST":
            if not can_change:
                raise PermissionDenied
            if form.is_valid():
                try:
                    container.update_settings().execute(self.actor(request), form.cleaned_data)
                except DomainError as error:
                    show_service_error(form, error)
                else:
                    self.message_user(request, _("The settings were saved."), messages.SUCCESS)
                    return HttpResponseRedirect(request.path)
        if not can_change:
            for field in form.fields.values():
                field.disabled = True
        return _form_page(
            self,
            request,
            form,
            title=_("System settings"),
            submit_label=_("Save") if can_change else None,
        )


def _form_page(model_admin, request, form, *, title, submit_label, subtitle=None, cancel_url=None):
    context = {
        **model_admin.admin_site.each_context(request),
        "title": title,
        "subtitle": subtitle,
        "opts": model_admin.model._meta,
        "form": form,
        "submit_label": submit_label,
        "cancel_url": cancel_url,
    }
    request.current_app = model_admin.admin_site.name
    return TemplateResponse(request, FORM_PAGE, context)


# --- Sidebar ------------------------------------------------------------------------------------

register_screen(Group.FACILITIES, model=Department, title=_("Departments"), icon="corporate_fare")
register_screen(Group.FACILITIES, model=Clinic, title=_("Clinics"), icon="apartment")
register_screen(Group.FACILITIES, model=Chair, title=_("Chairs"), icon="chair")
register_screen(Group.FACILITIES, model=Session, title=_("Sessions"), icon="schedule")
register_screen(Group.FACILITIES, model=Term, title=_("Terms"), icon="calendar_month")
register_screen(Group.LISTS, model=CaseType, title=_("Case types"), icon="category")
register_screen(Group.LISTS, model=ToothCode, title=_("Tooth codes"), icon="dentistry")
register_screen(
    Group.LISTS,
    model=MedicalHistoryItem,
    title=_("Medical history items"),
    icon="medical_information",
)
register_screen(Group.LISTS, model=SoftTissueSite, title=_("Soft tissue sites"), icon="body_system")
register_screen(Group.LISTS, model=IndexDefinition, title=_("Index definitions"), icon="grid_on")
register_screen(Group.LISTS, model=TreatmentType, title=_("Treatment types"), icon="healing")
register_screen(Group.LISTS, model=ChecklistItem, title=_("Checklist items"), icon="checklist")
register_screen(Group.LISTS, model=FaultCategory, title=_("Fault categories"), icon="report")
register_screen(Group.SETTINGS, model=SystemSetting, title=_("System settings"), icon="settings")
