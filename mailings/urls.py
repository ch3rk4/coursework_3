"""
URL-адреса для приложения рассылок.
"""

from django.urls import path
from . import views
from . import manager_views

app_name = 'mailings'

urlpatterns = [
    # === УПРАВЛЕНИЕ РАССЫЛКАМИ ===
    path('', views.MailingListView.as_view(), name='mailing_list'),
    path('create/', views.MailingCreateView.as_view(), name='mailing_create'),
    path('<int:pk>/', views.MailingDetailView.as_view(), name='mailing_detail'),
    path('<int:pk>/edit/', views.MailingUpdateView.as_view(), name='mailing_edit'),
    path('<int:pk>/delete/', views.MailingDeleteView.as_view(), name='mailing_delete'),
    path('<int:pk>/send/', views.MailingSendView.as_view(), name='mailing_send'),

    # === УПРАВЛЕНИЕ СООБЩЕНИЯМИ ===
    path('messages/', views.MessageListView.as_view(), name='message_list'),
    path('messages/create/', views.MessageCreateView.as_view(), name='message_create'),
    path('messages/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('messages/<int:pk>/edit/', views.MessageUpdateView.as_view(), name='message_edit'),
    path('messages/<int:pk>/delete/', views.MessageDeleteView.as_view(), name='message_delete'),

    # === УПРАВЛЕНИЕ КЛИЕНТАМИ ===
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_edit'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),

    # === СТАТИСТИКА И ОТЧЕТЫ ===
    path('attempts/', views.MailingAttemptListView.as_view(), name='attempt_list'),
    path('attempts/<int:pk>/', views.MailingAttemptDetailView.as_view(), name='attempt_detail'),
    path('stats/', views.MailingStatsView.as_view(), name='mailing_stats'),

    # === МЕНЕДЖЕРСКИЕ ФУНКЦИИ ===
    path('manager/', manager_views.ManagerDashboardView.as_view(), name='manager_dashboard'),
    path('manager/mailings/', manager_views.ManagerMailingListView.as_view(), name='manager_mailing_list'),
    path('manager/users/', manager_views.ManagerUserListView.as_view(), name='manager_user_list'),
    path('manager/toggle-user/<int:user_id>/', manager_views.toggle_user_active, name='manager_toggle_user'),
    path('manager/toggle-mailing/<int:mailing_id>/', manager_views.toggle_mailing_status, name='manager_toggle_mailing'),
]