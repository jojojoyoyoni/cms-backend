from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cases'

    def ready(self):
        # Import the signals so they are registered
        import apps.cases.signals