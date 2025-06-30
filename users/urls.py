"""
URL-адреса для приложения пользователей.
"""

from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Регистрация нового пользователя
    path('register/', views.RegisterView.as_view(), name='register'),

    # Вход в систему
    path('login/', views.CustomLoginView.as_view(), name='login'),

    # Выход из системы
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Просмотр профиля
    path('profile/', views.ProfileView.as_view(), name='profile'),

    # Редактирование профиля
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),

    # Подтверждение email (для будущего использования)
    path('email-confirm/<str:token>/', views.EmailConfirmView.as_view(), name='email_confirm'),
]