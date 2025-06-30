from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Кастомная модель пользователя, расширяющая стандартную модель Django.

    Наследуемся от AbstractUser, чтобы сохранить всю базовую функциональность
    Django (логин, пароль, права доступа), но добавить свои поля.
    """

    # Переопределяем поле email, делая его обязательным и уникальным
    email = models.EmailField(
        unique=True,
        verbose_name='Email адрес',
        help_text='Обязательное поле. Используется для входа в систему.'
    )

    # Дополнительные поля профиля
    avatar = models.ImageField(
        upload_to='users/avatars/',
        null=True,
        blank=True,
        verbose_name='Аватар'
    )

    phone = models.CharField(
        max_length=35,
        null=True,
        blank=True,
        verbose_name='Номер телефона'
    )

    country = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Страна'
    )

    # Указываем, что для входа будет использоваться email вместо username
    USERNAME_FIELD = 'email'
    # Убираем email из REQUIRED_FIELDS, так как он уже указан как USERNAME_FIELD
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """
        Строковое представление пользователя.
        Возвращаем email или username, если email пустой.
        """
        return self.email or self.username