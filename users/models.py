from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    """
    Кастомный менеджер для модели пользователя.

    Переопределяет методы создания пользователей для работы с email
    вместо username в качестве основного поля аутентификации.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Создает и сохраняет обычного пользователя с email и паролем.
        """
        if not email:
            raise ValueError('Email адрес обязателен')

        email = self.normalize_email(email)

        # Устанавливаем username равным email для совместимости
        extra_fields.setdefault('username', email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Создает и сохраняет суперпользователя с email и паролем.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


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

    # Подключаем кастомный менеджер
    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """
        Строковое представление пользователя.
        Возвращаем email или username, если email пустой.
        """
        return self.email or self.username