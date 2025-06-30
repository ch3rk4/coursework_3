from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Настраиваем админ-панель для нашей кастомной модели пользователя.

    Наследуемся от стандартного UserAdmin, чтобы сохранить всю базовую
    функциональность, но адаптируем под наши дополнительные поля.
    """

    # Поля для отображения в списке пользователей
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff', 'is_active')

    # Поля для поиска
    search_fields = ('email', 'username', 'first_name', 'last_name')

    # Фильтры в боковой панели
    list_filter = ('is_staff', 'is_active', 'date_joined', 'country')

    # Сортировка по умолчанию
    ordering = ('email',)

    # Настройка формы редактирования пользователя
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('avatar', 'phone', 'country')
        }),
    )

    # Настройка формы создания пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('email', 'avatar', 'phone', 'country')
        }),
    )