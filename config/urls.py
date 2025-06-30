"""
URL configuration for mailing service project
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from mailings.views import HomeView

urlpatterns = [
    # Админ-панель Django
    path('admin/', admin.site.urls),

    # Главная страница
    path('', HomeView.as_view(), name='home'),

    # URL-адреса приложения пользователей (аутентификация)
    path('users/', include('users.urls')),

    # URL-адреса приложения рассылок
    path('mailings/', include('mailings.urls')),
]

# Настройка для работы с медиа-файлами в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])