from django.db import models
from django.conf import settings


class Client(models.Model):
    """
    Модель получателя рассылки (клиента).

    Каждый клиент представляет человека, которому можем отправлять письма.
    Думайте о клиенте как о контакте в вашей адресной книге.
    """

    email = models.EmailField(
        unique=True,
        verbose_name='Email адрес',
        help_text='Уникальный email адрес клиента'
    )

    full_name = models.CharField(
        max_length=200,
        verbose_name='Полное имя'
    )

    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий',
        help_text='Дополнительная информация о клиенте'
    )

    # Связь с пользователем (владельцем клиента)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец',
        help_text='Пользователь, который создал этого клиента'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        # Права доступа для менеджеров
        permissions = [
            ('view_all_clients', 'Может просматривать всех клиентов'),
            ('disable_client', 'Может отключать клиентов'),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.email})'


class Message(models.Model):
    """
    Модель сообщения для рассылки.

    Это шаблон письма, которое будет отправлено.
    Как заготовка письма, которую можно использовать многократно.
    """

    subject = models.CharField(
        max_length=200,
        verbose_name='Тема письма'
    )

    body = models.TextField(
        verbose_name='Тело письма'
    )

    # Связь с пользователем (владельцем сообщения)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        # Права доступа для менеджеров
        permissions = [
            ('view_all_messages', 'Может просматривать все сообщения'),
            ('disable_message', 'Может отключать сообщения'),
        ]

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """
    Модель рассылки.

    Это основная сущность, которая объединяет сообщение, получателей
    и параметры отправки. Думайте о рассылке как о кампании по отправке писем.
    """

    # Статусы рассылки
    STATUS_CREATED = 'created'
    STATUS_STARTED = 'started'
    STATUS_COMPLETED = 'completed'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_STARTED, 'Запущена'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    # Основные поля рассылки
    name = models.CharField(
        max_length=200,
        verbose_name='Название рассылки',
        help_text='Описательное название для удобства'
    )

    first_send_datetime = models.DateTimeField(
        verbose_name='Дата и время первой отправки'
    )

    end_datetime = models.DateTimeField(
        verbose_name='Дата и время окончания отправки'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name='Статус'
    )

    # Связи с другими моделями
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name='Сообщение'
    )

    clients = models.ManyToManyField(
        Client,
        verbose_name='Получатели',
        help_text='Клиенты, которым будет отправлена рассылка'
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Владелец'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        # Права доступа для менеджеров
        permissions = [
            ('view_all_mailings', 'Может просматривать все рассылки'),
            ('disable_mailing', 'Может отключать рассылки'),
        ]

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'


class MailingAttempt(models.Model):
    """
    Модель попытки рассылки.

    Каждый раз, когда система пытается отправить письмо в рамках рассылки,
    создается запись попытки. Это позволяет отслеживать успешность отправки
    и собирать статистику.
    """

    # Статусы попытки
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_FAILED, 'Не успешно'),
    ]

    datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время попытки'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='Статус'
    )

    server_response = models.TextField(
        blank=True,
        verbose_name='Ответ почтового сервера',
        help_text='Подробная информация об ошибке или подтверждении'
    )

    # Связь с рассылкой
    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        verbose_name='Рассылка'
    )

    # Информация о получателе (сохраняем для статистики)
    client_email = models.EmailField(
        verbose_name='Email получателя'
    )

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылки'
        # Сортировка по умолчанию - новые попытки сверху
        ordering = ['-datetime']

    def __str__(self):
        return f'{self.mailing.name} - {self.client_email} ({self.get_status_display()})'