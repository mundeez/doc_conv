from django.apps import AppConfig


class Md2DocxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'md2docx'

    def ready(self):
        """Import signals when the app is ready."""
        from . import signals  # noqa: F401
