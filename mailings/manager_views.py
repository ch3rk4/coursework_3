"""
Представления для менеджеров
"""

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model

from .models import Mailing, Message, Client, MailingAttempt
from .decorators import ManagerRequiredMixin
from .cache import invalidate_user_cache, invalidate_mailing_cache

User = get_user_model()


class ManagerMailingListView(ManagerRequiredMixin, ListView):
    """Список всех рассылок для менеджеров"""

    model = Mailing
    template_name = 'mailings/manager/mailing_list.html'
    context_object_name = 'mailings'
    paginate_by = 20

    def get_queryset(self):
        queryset = Mailing.objects.select_related('owner', 'message').order_by('-created_at')

        # Фильтры
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset


class ManagerUserListView(ManagerRequiredMixin, ListView):
    """Список всех пользователей для менеджеров"""

    model = User
    template_name = 'mailings/manager/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.order_by('-date_joined')


@method_decorator(login_required, name='dispatch')
class ManagerDashboardView(ManagerRequiredMixin, ListView):
    """Панель управления для менеджеров"""

    model = Mailing
    template_name = 'mailings/manager/dashboard.html'
    context_object_name = 'recent_mailings'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Общая статистика
        context.update({
            'total_users': User.objects.count(),
            'total_mailings': Mailing.objects.count(),
            'active_mailings': Mailing.objects.filter(status=Mailing.STATUS_STARTED).count(),
            'total_attempts': MailingAttempt.objects.count(),
            'recent_users': User.objects.order_by('-date_joined')[:5],
        })

        return context


@require_POST
@login_required
def toggle_user_active(request, user_id):
    """Блокировка/разблокировка пользователя"""

    if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
        return JsonResponse({'error': 'Нет прав доступа'}, status=403)

    user = get_object_or_404(User, id=user_id)

    # Нельзя блокировать себя или суперпользователей
    if user == request.user or user.is_superuser:
        return JsonResponse({'error': 'Нельзя заблокировать этого пользователя'}, status=400)

    user.is_active = not user.is_active
    user.save()

    action = "активирован" if user.is_active else "заблокирован"
    messages.success(request, f'Пользователь {user.email} {action}')

    return JsonResponse({
        'success': True,
        'is_active': user.is_active,
        'message': f'Пользователь {action}'
    })


@require_POST
@login_required
def toggle_mailing_status(request, mailing_id):
    """Отключение/включение рассылки менеджером"""

    if not (request.user.is_superuser or getattr(request.user, 'is_manager', False)):
        return JsonResponse({'error': 'Нет прав доступа'}, status=403)

    mailing = get_object_or_404(Mailing, id=mailing_id)

    # Менеджеры не могут редактировать свои рассылки через эту функцию
    if mailing.owner == request.user:
        return JsonResponse({'error': 'Используйте обычное редактирование для своих рассылок'}, status=400)

    # Переключаем статус
    if mailing.status == Mailing.STATUS_STARTED:
        mailing.status = Mailing.STATUS_COMPLETED
        action = "отключена"
    else:
        mailing.status = Mailing.STATUS_STARTED
        action = "активирована"

    mailing.save()

    # Инвалидируем кеш
    invalidate_user_cache(mailing.owner.id)
    invalidate_mailing_cache(mailing.id)

    messages.success(request, f'Рассылка "{mailing.name}" {action}')

    return JsonResponse({
        'success': True,
        'status': mailing.status,
        'status_display': mailing.get_status_display(),
        'message': f'Рассылка {action}'
    })