from django.apps import AppConfig


class MatchesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.matches"
    label = "matches"

    def ready(self) -> None:
        from . import signals  # noqa: F401
