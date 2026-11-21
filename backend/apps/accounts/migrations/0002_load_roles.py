"""Loads the six roles (design section 8). Names are data the administrator may edit later;
the codes are fixed because the permission classes use them."""

from django.db import migrations

ROLES = [
    ("super_admin", "مدير النظام", "System administrator"),
    ("management", "الإدارة", "Management"),
    ("reception", "الاستقبال", "Reception"),
    ("supervisor", "مشرف", "Supervisor"),
    ("student", "طالب", "Student"),
    ("technician", "فني صيانة", "Maintenance technician"),
]


def load_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, name_ar, name_en in ROLES:
        Role.objects.get_or_create(code=code, defaults={"name_ar": name_ar, "name_en": name_en})


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(load_roles, migrations.RunPython.noop),
    ]
