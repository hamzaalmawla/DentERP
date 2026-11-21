"""accounts.0001 must not depend on core: core.0001 already depends on the user model."""

from django.db.migrations.loader import MigrationLoader


def test_accounts_migrations_do_not_depend_on_core(db):
    loader = MigrationLoader(None, ignore_no_migrations=True)

    for (app, _name), migration in loader.disk_migrations.items():
        if app == "accounts":
            assert all(dep_app != "core" for dep_app, _ in migration.dependencies)


def test_core_runs_after_the_user_model(db):
    loader = MigrationLoader(None, ignore_no_migrations=True)
    plan = loader.graph.forwards_plan(("core", "0001_initial"))

    assert ("accounts", "0001_initial") in plan
