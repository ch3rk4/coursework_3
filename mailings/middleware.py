"""
Middleware для управления правами доступа.
"""

from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.contrib.auth.models import Group
from django.urls import resolve
from django.contrib.auth import get_user_model

User = get_user_model()


class PermissionsMiddleware:
    """
    Middleware для проверки прав доступа к различным разделам системы.

    Логика работы:
    - Обычные пользователи видят только свои данные
    - Менеджеры могут просматривать все данные, но не редактировать чужие
    - Администраторы имеют полный доступ ко всему
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Основная логика middleware."""

        # Проверяем права доступа перед обработкой запроса
        if request.user.is_authenticated:
            # Добавляем информацию о роли пользователя в request
            request.user.is_manager = self.is_manager(request.user)
            request.user.role_display = self.get_user_role_display(request.user)

        response = self.get_response(request)
        return response

    def is_manager(self, user):
        """Проверяет, является ли пользователь менеджером."""
        if user.is_superuser:
            return True

        try:
            managers_group = Group.objects.get(name='Менеджеры')
            return managers_group in user.groups.all()
        except Group.DoesNotExist:
            return False

    def get_user_role_display(self, user):
        """Возвращает отображаемое название роли пользователя."""
        if user.is_superuser:
            return 'Администратор'
        elif self.is_manager(user):
            return 'Менеджер'
        else:
            return 'Пользователь'


class ManagerAccessMixin:
    """
    Миксин для представлений, которые требуют прав менеджера.

    Используется для ограничения доступа к административным функциям.
    """

    def dispatch(self, request, *args, **kwargs):
        """Проверяем права доступа перед выполнением представления."""

        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Проверяем, является ли пользователь менеджером или администратором
        if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
            return HttpResponseForbidden(
                render(request, 'errors/403.html', {
                    'message': 'У вас нет прав доступа к этому разделу.'
                })
            )

        return super().dispatch(request, *args, **kwargs)


def check_object_ownership(user, obj):
    """
    Проверяет, может ли пользователь редактировать объект.

    Args:
        user: Пользователь
        obj: Объект для проверки (должен иметь поле owner)

    Returns:
        bool: True, если пользователь может редактировать объект
    """

    # Администраторы могут редактировать всё
    if user.is_superuser:
        return True

    # Владельцы могут редактировать свои объекты
    if hasattr(obj, 'owner') and obj.owner == user:
        return True

    # Менеджеры могут только просматривать, но не редактировать чужие объекты
    return False


def get_accessible_objects(model, user, action='view'):
    """
    Возвращает объекты, доступные пользователю в зависимости от его роли.

    Args:
        model: Модель для фильтрации
        user: Пользователь
        action: Тип действия ('view', 'edit', 'delete')

    Returns:
        QuerySet: Отфильтрованные объекты
    """

    # Администраторы видят всё
    if user.is_superuser:
        return model.objects.all()

    # Менеджеры могут просматривать всё, но редактировать только своё
    if getattr(user, 'is_manager', False):
        if action == 'view':
            return model.objects.all()
        else:
            return model.objects.filter(owner=user)

    # Обычные пользователи видят только своё
    return model.objects.filter(owner=user)