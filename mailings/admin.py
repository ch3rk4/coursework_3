from django.contrib import admin

from .models import Client, Mailing, MailingAttempt, Message


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """
    Настройка админ-панели для модели Клиент.

    Админ-панель - это наш инструмент для управления данными во время разработки
    и для менеджеров в будущем. Думайте о ней как о удобном интерфейсе
    для просмотра и редактирования записей в базе данных.
    """

    list_display = ("full_name", "email", "owner", "created_at")
    list_filter = ("owner", "created_at")
    search_fields = ("full_name", "email", "comment")
    readonly_fields = ("created_at",)

    # Группируем поля для удобства
    fieldsets = (
        ("Основная информация", {"fields": ("full_name", "email", "comment")}),
        (
            "Системная информация",
            {
                "fields": ("owner", "created_at"),
                "classes": ("collapse",),  # Сворачиваемая секция
            },
        ),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Настройка админ-панели для модели Сообщение."""

    list_display = ("subject", "owner", "created_at")
    list_filter = ("owner", "created_at")
    search_fields = ("subject", "body")
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Содержание сообщения", {"fields": ("subject", "body")}),
        (
            "Системная информация",
            {"fields": ("owner", "created_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    """Настройка админ-панели для модели Рассылка."""

    list_display = ("name", "status", "first_send_datetime", "end_datetime", "owner")
    list_filter = ("status", "owner", "created_at", "first_send_datetime")
    search_fields = ("name", "message__subject")
    readonly_fields = ("created_at",)

    # Настраиваем отображение связанных полей
    filter_horizontal = ("clients",)  # Удобный виджет для ManyToMany

    fieldsets = (
        ("Основная информация", {"fields": ("name", "status")}),
        ("Временные параметры", {"fields": ("first_send_datetime", "end_datetime")}),
        ("Содержание и получатели", {"fields": ("message", "clients")}),
        (
            "Системная информация",
            {"fields": ("owner", "created_at"), "classes": ("collapse",)},
        ),
    )

    # Настройка действий (actions)
    def make_active(self, request, queryset):
        """Действие для активации рассылок."""
        updated = queryset.update(status=Mailing.STATUS_STARTED)
        self.message_user(request, f"Активировано {updated} рассылок.")

    make_active.short_description = "Активировать выбранные рассылки"

    actions = [make_active]


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    """Настройка админ-панели для модели Попытка рассылки."""

    list_display = ("mailing", "client_email", "status", "datetime")
    list_filter = ("status", "datetime", "mailing__name")
    search_fields = ("client_email", "mailing__name", "server_response")
    readonly_fields = ("datetime",)

    # Делаем все поля только для чтения, так как попытки не должны редактироваться
    def has_change_permission(self, request, obj=None):
        """Запрещаем редактирование попыток - они создаются автоматически."""
        return False

    def has_add_permission(self, request):
        """Запрещаем ручное создание попыток."""
        return False

    fieldsets = (
        ("Информация о попытке", {"fields": ("datetime", "status", "server_response")}),
        ("Связанные данные", {"fields": ("mailing", "client_email")}),
    )
