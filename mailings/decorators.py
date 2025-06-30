"""
Декораторы для проверки прав доступа
"""

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied


def manager_required(view_func):
    """
    Декоратор, требующий права менеджера для доступа к представлению.

    Использование:
        @manager_required
        def my_view(request):
            ...
    """

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        # Проверяем, является ли пользователь менеджером или администратором
        if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
            return HttpResponseForbidden(
                render(request, 'errors/403.html', {
                    'message': 'Для доступа к этой странице требуются права менеджера.'
                })
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def owner_or_manager_required(model_class, pk_param='pk'):
    """
    Декоратор, разрешающий доступ владельцу объекта или менеджеру.

    Args:
        model_class: Класс модели для проверки
        pk_param: Название параметра с ID объекта в URL

    Использование:
        @owner_or_manager_required(MyModel)
        def my_view(request, pk):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Получаем ID объекта из kwargs
            object_id = kwargs.get(pk_param)
            if not object_id:
                raise PermissionDenied("Объект не найден")

            # Получаем объект или возвращаем 404
            obj = get_object_or_404(model_class, pk=object_id)

            # Проверяем права доступа
            if not (
                    request.user.is_superuser or
                    getattr(request.user, 'is_manager', False) or
                    (hasattr(obj, 'owner') and obj.owner == request.user)
            ):
                return HttpResponseForbidden(
                    render(request, 'errors/403.html', {
                        'message': 'У вас нет прав для доступа к этому объекту.'
                    })
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def owner_required(model_class, pk_param='pk'):
    """
    Декоратор, разрешающий доступ только владельцу объекта или администратору.

    Args:
        model_class: Класс модели для проверки
        pk_param: Название параметра с ID объекта в URL

    Использование:
        @owner_required(MyModel)
        def my_edit_view(request, pk):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Получаем ID объекта из kwargs
            object_id = kwargs.get(pk_param)
            if not object_id:
                raise PermissionDenied("Объект не найден")

            # Получаем объект или возвращаем 404
            obj = get_object_or_404(model_class, pk=object_id)

            # Проверяем права доступа (только владелец или администратор)
            if not (
                    request.user.is_superuser or
                    (hasattr(obj, 'owner') and obj.owner == request.user)
            ):
                return HttpResponseForbidden(
                    render(request, 'errors/403.html', {
                        'message': 'Только владелец объекта может выполнить это действие.'
                    })
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


class ManagerRequiredMixin:
    """
    Миксин для представлений, требующих права менеджера.

    Использование в классах-представлениях:
        class MyView(ManagerRequiredMixin, ListView):
            ...
    """

    def dispatch(self, request, *args, **kwargs):
        """Проверяем права перед выполнением представления."""

        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Проверяем права менеджера
        if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
            return HttpResponseForbidden(
                render(request, 'errors/403.html', {
                    'message': 'Для доступа к этой странице требуются права менеджера.'
                })
            )

        return super().dispatch(request, *args, **kwargs)


class OwnerOrManagerRequiredMixin:
    """
    Миксин для представлений, доступных владельцу или менеджеру.

    Автоматически фильтрует QuerySet по правам доступа.
    """

    def get_queryset(self):
        """Фильтруем объекты по правам доступа."""
        queryset = super().get_queryset()

        if not self.request.user.is_authenticated:
            return queryset.none()

        # Администраторы и менеджеры видят всё
        if (self.request.user.is_superuser or
                getattr(self.request.user, 'is_manager', False)):
            return queryset

        # Обычные пользователи видят только свои объекты
        if hasattr(queryset.model, 'owner'):
            return queryset.filter(owner=self.request.user)

        return queryset


class OwnerRequiredMixin:
    """
    Миксин для представлений, доступных только владельцу.

    Проверяет, что пользователь является владельцем объекта
    или администратором системы.
    """

    def get_object(self, queryset=None):
        """Получаем объект с проверкой прав доступа."""
        obj = super().get_object(queryset)

        # Проверяем права доступа
        if not (
                self.request.user.is_superuser or
                (hasattr(obj, 'owner') and obj.owner == self.request.user)
        ):
            raise PermissionDenied(
                "У вас нет прав для доступа к этому объекту."
            )

        return obj


def user_can_edit_object(user, obj):
    """
    Проверяет, может ли пользователь редактировать объект.

    Args:
        user: Пользователь
        obj: Объект для проверки

    Returns:
        bool: True, если пользователь может редактировать объект
    """
    if not user.is_authenticated:
        return False

    # Администраторы могут редактировать всё
    if user.is_superuser:
        return True

    # Владельцы могут редактировать свои объекты
    if hasattr(obj, 'owner') and obj.owner == user:
        return True

    return False


def user_can_view_object(user, obj):
    """
    Проверяет, может ли пользователь просматривать объект.

    Args:
        user: Пользователь
        obj: Объект для проверки

    Returns:
        bool: True, если пользователь может просматривать объект
    """
    if not user.is_authenticated:
        return False

    # Администраторы и менеджеры могут просматривать всё
    if (user.is_superuser or getattr(user, 'is_manager', False)):
        return True

    # Владельцы могут просматривать свои объекты
    if hasattr(obj, 'owner') and obj.owner == user:
        return True

    return False