from django.apps import AppConfig


class MailingsConfig(AppConfig):
    """
    Конфигурация приложения рассылок.
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailings'
    verbose_name = 'Рассылки'