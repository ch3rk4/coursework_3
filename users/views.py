"""
Представления для приложения пользователей
"""

from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login
from django.views.generic import CreateView, DetailView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from .models import User
from .forms import UserRegistrationForm, UserProfileForm


class RegisterView(CreateView):
    """
    Представление для регистрации новых пользователей.

    CreateView - это встроенный класс Django, который автоматически
    обрабатывает создание объектов. Мы просто указываем модель,
    форму и шаблон, а Django сделает всю работу за нас.
    """

    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        """
        Метод вызывается, когда форма прошла валидацию.

        Здесь мы можем добавить дополнительную логику перед
        сохранением пользователя в базу данных.
        """

        # Сохраняем пользователя
        response = super().form_valid(form)

        # Автоматически входим в систему после регистрации
        login(self.request, self.object)

        # Отправляем приветственное письмо (опционально)
        self.send_welcome_email()

        # Показываем сообщение об успехе
        messages.success(
            self.request,
            'Добро пожаловать! Ваш аккаунт успешно создан.'
        )

        return response

    def send_welcome_email(self):
        """Отправка приветственного письма новому пользователю."""
        try:
            send_mail(
                subject='Добро пожаловать в сервис рассылок!',
                message=f'Здравствуйте, {self.object.first_name or self.object.email}!\n\n'
                        f'Спасибо за регистрацию в нашем сервисе рассылок. '
                        f'Теперь вы можете создавать и управлять своими рассылками.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[self.object.email],
                fail_silently=True  # Не прерываем процесс при ошибке отправки
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем регистрацию
            print(f"Ошибка отправки приветственного письма: {e}")


class CustomLoginView(LoginView):
    """
    Кастомное представление для входа в систему.

    Наследуемся от встроенного LoginView и настраиваем под наши нужды.
    """

    template_name = 'users/login.html'
    redirect_authenticated_user = True  # Перенаправляем уже авторизованных

    def get_success_url(self):
        """Определяем, куда перенаправить после успешного входа."""
        return reverse_lazy('home')

    def form_valid(self, form):
        """Добавляем сообщение об успешном входе."""
        messages.success(self.request, f'Добро пожаловать, {form.get_user()}!')
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Кастомное представление для выхода из системы."""

    next_page = reverse_lazy('home')

    def dispatch(self, request, *args, **kwargs):
        """Добавляем сообщение об успешном выходе."""
        if request.user.is_authenticated:
            messages.info(request, 'Вы успешно вышли из системы.')
        return super().dispatch(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, DetailView):
    """
    Представление для просмотра профиля пользователя.

    LoginRequiredMixin - это миксин, который автоматически проверяет,
    что пользователь авторизован. Если нет - перенаправляет на страницу входа.
    """

    model = User
    template_name = 'users/profile.html'
    context_object_name = 'profile_user'

    def get_object(self):
        """Возвращаем текущего авторизованного пользователя."""
        return self.request.user


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования профиля пользователя."""

    model = User
    form_class = UserProfileForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        """Возвращаем текущего авторизованного пользователя."""
        return self.request.user

    def form_valid(self, form):
        """Добавляем сообщение об успешном обновлении."""
        messages.success(self.request, 'Профиль успешно обновлен!')
        return super().form_valid(form)


class EmailConfirmView(TemplateView):
    """
    Представление для подтверждения email.

    Пока что это заглушка для будущей функциональности.
    В реальном проекте здесь была бы логика проверки токена
    и активации аккаунта пользователя.
    """

    template_name = 'users/email_confirm.html'

    def get_context_data(self, **kwargs):
        """Добавляем дополнительные данные в контекст шаблона."""
        context = super().get_context_data(**kwargs)
        context['token'] = kwargs.get('token')
        return context