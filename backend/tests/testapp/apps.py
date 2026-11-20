from django.apps import AppConfig


class TestAppConfig(AppConfig):
    """Installed only by config.settings.test: models and endpoints that exercise core."""

    name = "tests.testapp"
    label = "testapp"
