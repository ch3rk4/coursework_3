"""
URL-адреса для приложения рассылок.
"""

from django.urls import path
from . import views

app_name = 'mailings'

urlpatterns = [
    # === УПРАВЛЕНИЕ РАССЫЛКАМИ ===

    # Список всех рассылок пользователя
    path('', views.MailingListView.as_view(), name='mailing_list'),

    # Создание новой рассылки
    path('create/', views.MailingCreateView.as_view(), name='mailing_create'),

    # Просмотр детальной информации о рассылке
    path('<int:pk>/', views.MailingDetailView.as_view(), name='mailing_detail'),

    # Редактирование рассылки
    path('<int:pk>/edit/', views.MailingUpdateView.as_view(), name='mailing_edit'),

    # Удаление рассылки
    path('<int:pk>/delete/', views.MailingDeleteView.as_view(), name='mailing_delete'),

    # Ручная отправка рассылки
    path('<int:pk>/send/', views.MailingSendView.as_view(), name='mailing_send'),

    # === УПРАВЛЕНИЕ СООБЩЕНИЯМИ ===

    # Список сообщений
    path('messages/', views.MessageListView.as_view(), name='message_list'),

    # Создание сообщения
    path('messages/create/', views.MessageCreateView.as_view(), name='message_create'),

    # Просмотр сообщения
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),

    # Редактирование сообщения
    path('messages/<int:pk>/edit/', views.MessageUpdateView.as_view(), name='message_edit'),

    # Удаление сообщения
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='message_delete'),

    # === УПРАВЛЕНИЕ КЛИЕНТАМИ ===

    # Список клиентов
    path('clients/', views.ClientListView.as_view(), name='client_list'),

    # Создание клиента
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),

    # Просмотр клиента
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),

    # Редактирование клиента
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),

    # Удаление клиента
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # === СТАТИСТИКА И ОТЧЕТЫ ===

    # Попытки рассылок (логи)
    path('attempts/', views.MailingAttemptListView.as_view(), name='attempt_list'),

    # Детали попытки рассылки
    path('attempts/<int:pk>/', views.MailingAttemptDetailView.as_view(), name='attempt_detail'),

    # Статистика по рассылкам пользователя
    path('stats/', views.MailingStatsView.as_view(), name='mailing_stats'),
]