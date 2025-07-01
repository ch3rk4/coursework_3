"""
Утилиты для работы с кешем.
"""

import hashlib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Client, Mailing, MailingAttempt, Message


def get_cache_key(prefix, *args, **kwargs):
    """
    Генерирует уникальный ключ кеша на основе переданных параметров.

    Args:
        prefix (str): Префикс для ключа
        *args: Позиционные аргументы
        **kwargs: Именованные аргументы

    Returns:
        str: Уникальный ключ кеша
    """
    # Создаем строку из всех параметров
    cache_string = f"{prefix}:" + ":".join(str(arg) for arg in args)
    if kwargs:
        cache_string += ":" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

    # Используем хеш для длинных ключей
    if len(cache_string) > 100:
        cache_string = f"{prefix}:{hashlib.md5(cache_string.encode()).hexdigest()}"

    return cache_string


def get_or_set_cache(cache_key, callable_func, timeout=None):
    """
    Получает данные из кеша или вычисляет и сохраняет их.

    Args:
        cache_key (str): Ключ кеша
        callable_func (callable): Функция для вычисления данных
        timeout (int): Время жизни кеша в секундах

    Returns:
        Данные из кеша или результат выполнения функции
    """
    if not settings.CACHE_ENABLED:
        return callable_func()

    # Пытаемся получить из кеша
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    # Вычисляем данные
    data = callable_func()

    # Сохраняем в кеш
    cache.set(cache_key, data, timeout or 300)  # 5 минут по умолчанию

    return data


def cache_user_stats(user_id, timeout=600):  # 10 минут
    """
    Кеширует статистику пользователя.

    Args:
        user_id (int): ID пользователя
        timeout (int): Время жизни кеша

    Returns:
        dict: Статистика пользователя
    """
    cache_key = get_cache_key("user_stats", user_id)

    def calculate_stats():

        return {
            "total_mailings": Mailing.objects.filter(owner_id=user_id).count(),
            "total_messages": Message.objects.filter(owner_id=user_id).count(),
            "total_clients": Client.objects.filter(owner_id=user_id).count(),
            "total_attempts": MailingAttempt.objects.filter(
                mailing__owner_id=user_id
            ).count(),
            "successful_attempts": MailingAttempt.objects.filter(
                mailing__owner_id=user_id, status=MailingAttempt.STATUS_SUCCESS
            ).count(),
            "active_mailings": Mailing.objects.filter(
                owner_id=user_id, status=Mailing.STATUS_STARTED
            ).count(),
        }

    return get_or_set_cache(cache_key, calculate_stats, timeout)


def cache_global_stats(timeout=900):  # 15 минут
    """
    Кеширует глобальную статистику системы.

    Args:
        timeout (int): Время жизни кеша

    Returns:
        dict: Глобальная статистика
    """
    cache_key = get_cache_key("global_stats")

    def calculate_stats():

        User = get_user_model()

        return {
            "total_users": User.objects.count(),
            "total_mailings": Mailing.objects.count(),
            "total_messages": Message.objects.count(),
            "total_clients": Client.objects.count(),
            "total_attempts": MailingAttempt.objects.count(),
            "successful_attempts": MailingAttempt.objects.filter(
                status=MailingAttempt.STATUS_SUCCESS
            ).count(),
            "failed_attempts": MailingAttempt.objects.filter(
                status=MailingAttempt.STATUS_FAILED
            ).count(),
            "active_mailings": Mailing.objects.filter(
                status=Mailing.STATUS_STARTED
            ).count(),
            "created_mailings": Mailing.objects.filter(
                status=Mailing.STATUS_CREATED
            ).count(),
            "completed_mailings": Mailing.objects.filter(
                status=Mailing.STATUS_COMPLETED
            ).count(),
        }

    return get_or_set_cache(cache_key, calculate_stats, timeout)


def cache_mailing_stats(mailing_id, timeout=300):  # 5 минут
    """
    Кеширует статистику конкретной рассылки.

    Args:
        mailing_id (int): ID рассылки
        timeout (int): Время жизни кеша

    Returns:
        dict: Статистика рассылки
    """
    cache_key = get_cache_key("mailing_stats", mailing_id)

    def calculate_stats():

        attempts = MailingAttempt.objects.filter(mailing_id=mailing_id)

        return {
            "total_attempts": attempts.count(),
            "successful_attempts": attempts.filter(
                status=MailingAttempt.STATUS_SUCCESS
            ).count(),
            "failed_attempts": attempts.filter(
                status=MailingAttempt.STATUS_FAILED
            ).count(),
            "latest_attempts": list(
                attempts.order_by("-datetime")[:10].values(
                    "client_email", "status", "datetime", "server_response"
                )
            ),
        }

    return get_or_set_cache(cache_key, calculate_stats, timeout)


def invalidate_user_cache(user_id):
    """
    Инвалидирует кеш для конкретного пользователя.

    Args:
        user_id (int): ID пользователя
    """
    if not settings.CACHE_ENABLED:
        return

    # Инвалидируем статистику пользователя
    cache_key = get_cache_key("user_stats", user_id)
    cache.delete(cache_key)

    # Инвалидируем глобальную статистику
    global_cache_key = get_cache_key("global_stats")
    cache.delete(global_cache_key)


def invalidate_mailing_cache(mailing_id):
    """
    Инвалидирует кеш для конкретной рассылки.

    Args:
        mailing_id (int): ID рассылки
    """
    if not settings.CACHE_ENABLED:
        return

    cache_key = get_cache_key("mailing_stats", mailing_id)
    cache.delete(cache_key)


def invalidate_all_cache():
    """Очищает весь кеш приложения."""
    if not settings.CACHE_ENABLED:
        return

    cache.clear()


class CacheMixin:
    """
    Миксин для представлений с поддержкой кеширования.

    Автоматически кеширует результаты get_context_data.
    """

    cache_timeout = 300  # 5 минут по умолчанию
    cache_prefix = "view"
    cache_per_user = True

    def get_cache_key(self):
        """Генерирует ключ кеша для представления."""
        args = [self.cache_prefix, self.__class__.__name__]

        if (
            self.cache_per_user
            and hasattr(self.request, "user")
            and self.request.user.is_authenticated
        ):
            args.append(f"user_{self.request.user.id}")

        # Добавляем параметры из URL
        if hasattr(self, "kwargs") and self.kwargs:
            args.extend(f"{k}_{v}" for k, v in self.kwargs.items())

        # Добавляем GET-параметры
        if self.request.GET:
            get_params = sorted(self.request.GET.items())
            args.extend(f"{k}_{v}" for k, v in get_params)

        return get_cache_key(*args)

    def get_context_data(self, **kwargs):
        """Кеширует контекст представления."""
        if not settings.CACHE_ENABLED:
            return super().get_context_data(**kwargs)

        cache_key = self.get_cache_key()

        def get_context():
            return super(CacheMixin, self).get_context_data(**kwargs)

        return get_or_set_cache(cache_key, get_context, self.cache_timeout)


def cache_template_fragment(fragment_name, *args, timeout=300):
    """
    Декоратор для кеширования фрагментов шаблонов.

    Args:
        fragment_name (str): Название фрагмента
        *args: Аргументы для создания уникального ключа
        timeout (int): Время жизни кеша

    Returns:
        function: Декоратор
    """

    def decorator(func):
        def wrapper(*func_args, **func_kwargs):
            if not settings.CACHE_ENABLED:
                return func(*func_args, **func_kwargs)

            cache_key = get_cache_key("template_fragment", fragment_name, *args)

            def get_content():
                return func(*func_args, **func_kwargs)

            return get_or_set_cache(cache_key, get_content, timeout)

        return wrapper

    return decorator


# Функции для управления кешем из админки
def get_cache_info():
    """
    Возвращает информацию о состоянии кеша.

    Returns:
        dict: Информация о кеше
    """
    if not settings.CACHE_ENABLED:
        return {"enabled": False}

    try:
        # Тестируем кеш
        test_key = "cache_test"
        test_value = "test_value"
        cache.set(test_key, test_value, 60)
        retrieved_value = cache.get(test_key)
        cache.delete(test_key)

        cache_working = retrieved_value == test_value

        return {
            "enabled": True,
            "working": cache_working,
            "backend": settings.CACHES["default"]["BACKEND"],
        }
    except Exception as e:
        return {
            "enabled": True,
            "working": False,
            "error": str(e),
        }


def warm_up_cache():
    """
    Предварительно прогревает кеш важными данными.

    Эта функция может быть вызвана после деплоя или периодически
    для обеспечения быстрого отклика приложения.
    """
    if not settings.CACHE_ENABLED:
        return

    # Прогреваем глобальную статистику
    cache_global_stats()

    # Прогреваем статистику активных пользователей
    User = get_user_model()

    active_users = User.objects.filter(
        last_login__gte=timezone.now() - timedelta(days=30)
    )[
        :20
    ]  # Топ-20 активных пользователей

    for user in active_users:
        cache_user_stats(user.id)


@receiver([post_save, post_delete])
def invalidate_cache_on_model_change(sender, instance, **kwargs):
    """
    Автоматически инвалидирует кеш при изменении моделей.

    Args:
        sender: Класс модели
        instance: Экземпляр модели
        **kwargs: Дополнительные параметры сигнала
    """
    from .models import Client, Mailing, MailingAttempt, Message

    if not settings.CACHE_ENABLED:
        return

    # Определяем, какой кеш нужно инвалидировать
    if sender in [Mailing, Message, Client]:
        if hasattr(instance, "owner"):
            invalidate_user_cache(instance.owner.id)
        invalidate_cache_on_model_change.__globals__["cache"].delete("global_stats")

    elif sender == MailingAttempt:
        if hasattr(instance, "mailing") and hasattr(instance.mailing, "owner"):
            invalidate_user_cache(instance.mailing.owner.id)
            invalidate_mailing_cache(instance.mailing.id)
        invalidate_cache_on_model_change.__globals__["cache"].delete("global_stats")
