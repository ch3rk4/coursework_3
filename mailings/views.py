"""
Представления для приложения рассылок.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from django.core.cache import cache

from .models import Mailing, Message, Client, MailingAttempt
from .forms import MailingForm, MessageForm, ClientForm
from .decorators import (
    OwnerRequiredMixin, OwnerOrManagerRequiredMixin,
    user_can_edit_object, user_can_view_object
)
from .cache import (
    cache_global_stats, cache_user_stats, cache_mailing_stats,
    CacheMixin, invalidate_user_cache, invalidate_mailing_cache
)


class HomeView(CacheMixin, TemplateView):
    """
    Главная страница сайта.

    Отображает общую статистику по всем рассылкам в системе.
    Это первое, что видит пользователь при заходе на сайт.

    Использует кеширование для улучшения производительности.
    """

    template_name = 'mailings/home.html'
    cache_timeout = 900  # 15 минут
    cache_per_user = False  # Глобальная статистика одинаковая для всех

    def get_context_data(self, **kwargs):
        """
        Собираем статистику для главной страницы.

        Данные кешируются для снижения нагрузки на базу данных.
        """
        context = super().get_context_data(**kwargs)

        # Получаем закешированную глобальную статистику
        stats = cache_global_stats()
        context.update(stats)

        return context


# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ УПРАВЛЕНИЯ РАССЫЛКАМИ
# ============================================================================

# Удаляем старый миксин, так как теперь используем импортированный


class MailingListView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, ListView):
    """Список всех рассылок пользователя."""

    model = Mailing
    template_name = 'mailings/mailing_list.html'
    context_object_name = 'mailings'
    paginate_by = 10  # Показываем по 10 рассылок на странице

    def get_queryset(self):
        """Добавляем сортировку и возможность поиска."""
        queryset = super().get_queryset()

        # Поиск по названию рассылки
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)

        # Фильтр по статусу
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные для шаблона."""
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Mailing.STATUS_CHOICES
        context['current_search'] = self.request.GET.get('search', '')
        context['current_status'] = self.request.GET.get('status', '')
        return context


class MailingDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о рассылке."""

    model = Mailing
    template_name = 'mailings/mailing_detail.html'
    context_object_name = 'mailing'

    def get_context_data(self, **kwargs):
        """Добавляем статистику по попыткам отправки с кешированием."""
        context = super().get_context_data(**kwargs)

        # Получаем закешированную статистику рассылки
        stats = cache_mailing_stats(self.object.id)
        context.update(stats)

        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    """Создание новой рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def form_valid(self, form):
        """Устанавливаем владельца рассылки и инвалидируем кеш."""
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        # Инвалидируем кеш пользователя
        invalidate_user_cache(self.request.user.id)

        messages.success(self.request, 'Рассылка успешно создана!')
        return response

    def get_form_kwargs(self):
        """Передаем текущего пользователя в форму."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MailingUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование рассылки."""

    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def form_valid(self, form):
        """Добавляем сообщение об успешном обновлении и инвалидируем кеш."""
        response = super().form_valid(form)

        # Инвалидируем кеш пользователя и рассылки
        invalidate_user_cache(self.request.user.id)
        invalidate_mailing_cache(self.object.id)

        messages.success(self.request, 'Рассылка успешно обновлена!')
        return response

    def get_form_kwargs(self):
        """Передаем текущего пользователя в форму."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MailingDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление рассылки."""

    model = Mailing
    template_name = 'mailings/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def delete(self, request, *args, **kwargs):
        """Добавляем сообщение об успешном удалении и инвалидируем кеш."""
        mailing = self.get_object()
        user_id = mailing.owner.id
        mailing_id = mailing.id

        response = super().delete(request, *args, **kwargs)

        # Инвалидируем кеш пользователя и рассылки
        invalidate_user_cache(user_id)
        invalidate_mailing_cache(mailing_id)

        messages.success(request, 'Рассылка успешно удалена!')
        return response


class MailingSendView(LoginRequiredMixin, OwnerRequiredMixin, DetailView):
    """Ручная отправка рассылки."""

    model = Mailing

    def post(self, request, *args, **kwargs):
        """Обрабатываем запрос на отправку рассылки."""
        mailing = self.get_object()

        # Проверяем, что рассылка может быть отправлена
        if mailing.status == Mailing.STATUS_COMPLETED:
            messages.error(request, 'Эта рассылка уже завершена.')
            return redirect('mailings:mailing_detail', pk=mailing.pk)

        # Запускаем отправку
        success_count, total_count = self.send_mailing(mailing)

        # Обновляем статус рассылки
        if mailing.status == Mailing.STATUS_CREATED:
            mailing.status = Mailing.STATUS_STARTED
            mailing.save()

        # Инвалидируем кеш после отправки
        invalidate_user_cache(mailing.owner.id)
        invalidate_mailing_cache(mailing.id)

        # Показываем результат
        if success_count == total_count:
            messages.success(
                request,
                f'Рассылка успешно отправлена! '
                f'Доставлено {success_count} из {total_count} писем.'
            )
        else:
            messages.warning(
                request,
                f'Рассылка частично отправлена. '
                f'Доставлено {success_count} из {total_count} писем.'
            )

        return redirect('mailings:mailing_detail', pk=mailing.pk)

    def send_mailing(self, mailing):
        """
        Логика отправки рассылки.

        Проходим по всем клиентам рассылки и пытаемся отправить
        каждому письмо, сохраняя результат в MailingAttempt.
        """
        success_count = 0
        total_count = 0

        for client in mailing.clients.all():
            total_count += 1

            try:
                # Пытаемся отправить письмо
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[client.email],
                    fail_silently=False
                )

                # Создаем запись об успешной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    client_email=client.email,
                    status=MailingAttempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено'
                )

                success_count += 1

            except Exception as e:
                # Создаем запись о неуспешной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    client_email=client.email,
                    status=MailingAttempt.STATUS_FAILED,
                    server_response=str(e)
                )

        return success_count, total_count


# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ УПРАВЛЕНИЯ СООБЩЕНИЯМИ
# ============================================================================

class MessageListView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, ListView):
    """Список всех сообщений пользователя."""

    model = Message
    template_name = 'mailings/message_list.html'
    context_object_name = 'messages'
    paginate_by = 10

    def get_queryset(self):
        """Добавляем поиск по теме сообщения."""
        queryset = super().get_queryset()

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(subject__icontains=search_query)

        return queryset.order_by('-created_at')


class MessageDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о сообщении."""

    model = Message
    template_name = 'mailings/message_detail.html'
    context_object_name = 'message'


class MessageCreateView(LoginRequiredMixin, CreateView):
    """Создание нового сообщения."""

    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')

    def form_valid(self, form):
        """Устанавливаем владельца сообщения."""
        form.instance.owner = self.request.user
        messages.success(self.request, 'Сообщение успешно создано!')
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование сообщения."""

    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')

    def form_valid(self, form):
        """Добавляем сообщение об успешном обновлении."""
        messages.success(self.request, 'Сообщение успешно обновлено!')
        return super().form_valid(form)


class MessageDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление сообщения."""

    model = Message
    template_name = 'mailings/message_confirm_delete.html'
    success_url = reverse_lazy('mailings:message_list')

    def delete(self, request, *args, **kwargs):
        """Добавляем сообщение об успешном удалении."""
        messages.success(request, 'Сообщение успешно удалено!')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ УПРАВЛЕНИЯ КЛИЕНТАМИ
# ============================================================================

class ClientListView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, ListView):
    """Список всех клиентов пользователя."""

    model = Client
    template_name = 'mailings/client_list.html'
    context_object_name = 'clients'
    paginate_by = 15

    def get_queryset(self):
        """Добавляем поиск по имени и email."""
        queryset = super().get_queryset()

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(full_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        return queryset.order_by('full_name')


class ClientDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о клиенте."""

    model = Client
    template_name = 'mailings/client_detail.html'
    context_object_name = 'client'


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Создание нового клиента."""

    model = Client
    form_class = ClientForm
    template_name = 'mailings/client_form.html'
    success_url = reverse_lazy('mailings:client_list')

    def form_valid(self, form):
        """Устанавливаем владельца клиента."""
        form.instance.owner = self.request.user
        messages.success(self.request, 'Клиент успешно добавлен!')
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, OwnerRequiredMixin, UpdateView):
    """Редактирование клиента."""

    model = Client
    form_class = ClientForm
    template_name = 'mailings/client_form.html'
    success_url = reverse_lazy('mailings:client_list')

    def form_valid(self, form):
        """Добавляем сообщение об успешном обновлении."""
        messages.success(self.request, 'Данные клиента успешно обновлены!')
        return super().form_valid(form)


class ClientDeleteView(LoginRequiredMixin, OwnerRequiredMixin, DeleteView):
    """Удаление клиента."""

    model = Client
    template_name = 'mailings/client_confirm_delete.html'
    success_url = reverse_lazy('mailings:client_list')

    def delete(self, request, *args, **kwargs):
        """Добавляем сообщение об успешном удалении."""
        messages.success(request, 'Клиент успешно удален!')
        return super().delete(request, *args, **kwargs)


# ============================================================================
# ПРЕДСТАВЛЕНИЯ ДЛЯ СТАТИСТИКИ И ОТЧЕТОВ
# ============================================================================

class MailingAttemptListView(LoginRequiredMixin, ListView):
    """Список попыток рассылок пользователя."""

    model = MailingAttempt
    template_name = 'mailings/attempt_list.html'
    context_object_name = 'attempts'
    paginate_by = 20

    def get_queryset(self):
        """Показываем только попытки рассылок текущего пользователя или все для менеджеров."""
        queryset = super().get_queryset()

        # Администраторы и менеджеры видят все попытки
        if (self.request.user.is_superuser or
            getattr(self.request.user, 'is_manager', False)):
            return queryset.select_related('mailing').order_by('-datetime')

        # Обычные пользователи видят только попытки своих рассылок
        return queryset.filter(
            mailing__owner=self.request.user
        ).select_related('mailing').order_by('-datetime')


class MailingAttemptDetailView(LoginRequiredMixin, DetailView):
    """Детальная информация о попытке рассылки."""

    model = MailingAttempt
    template_name = 'mailings/attempt_detail.html'
    context_object_name = 'attempt'

    def get_queryset(self):
        """Ограничиваем доступ к попыткам в зависимости от роли пользователя."""
        queryset = super().get_queryset()

        # Администраторы и менеджеры видят все попытки
        if (self.request.user.is_superuser or
            getattr(self.request.user, 'is_manager', False)):
            return queryset

        # Обычные пользователи видят только попытки своих рассылок
        return queryset.filter(mailing__owner=self.request.user)


class MailingStatsView(LoginRequiredMixin, CacheMixin, TemplateView):
    """Страница со статистикой по рассылкам пользователя."""

    template_name = 'mailings/mailing_stats.html'
    cache_timeout = 600  # 10 минут
    cache_per_user = True

    def get_context_data(self, **kwargs):
        """Собираем подробную статистику для пользователя с кешированием."""
        context = super().get_context_data(**kwargs)

        # Определяем, какие данные показывать в зависимости от роли
        if (self.request.user.is_superuser or
            getattr(self.request.user, 'is_manager', False)):
            # Менеджеры и администраторы видят общую статистику
            stats = cache_global_stats()
            context['is_global_stats'] = True
        else:
            # Обычные пользователи видят только свою статистику
            stats = cache_user_stats(self.request.user.id)
            context['is_global_stats'] = False

        context.update(stats)

        # Дополнительные данные для графиков (не кешируем, так как они специфичны)
        if context['is_global_stats']:
            user_mailings = Mailing.objects.all()
            user_attempts = MailingAttempt.objects.all()
        else:
            user_mailings = Mailing.objects.filter(owner=self.request.user)
            user_attempts = MailingAttempt.objects.filter(
                mailing__owner=self.request.user
            )

        context.update({
            # Данные для графиков (последние рассылки)
            'recent_mailings': user_mailings.order_by('-created_at')[:5],
            'recent_attempts': user_attempts.order_by('-datetime')[:10],
        })

        # Вычисляем процент успешности
        if context['total_attempts'] > 0:
            context['success_rate'] = round(
                (context['successful_attempts'] / context['total_attempts']) * 100, 1
            )
        else:
            context['success_rate'] = 0

        return context