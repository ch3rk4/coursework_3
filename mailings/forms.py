"""
Формы для приложения рассылок.

Здесь мы создаем формы для всех основных моделей нашего приложения.
Формы не только обрабатывают ввод данных, но и обеспечивают безопасность,
валидацию и удобный пользовательский интерфейс.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Mailing, Message, Client


class ClientForm(forms.ModelForm):
    """
    Форма для создания и редактирования клиентов.

    Клиенты - это люди, которым мы отправляем рассылки.
    Форма должна быть простой и понятной, но при этом
    обеспечивать корректность введенных данных.
    """

    class Meta:
        model = Client
        fields = ['full_name', 'email', 'comment']

        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иван Иванович Иванов'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительная информация о клиенте...'
            }),
        }

        labels = {
            'full_name': 'Полное имя',
            'email': 'Email адрес',
            'comment': 'Комментарий',
        }

        help_texts = {
            'email': 'Уникальный email адрес клиента',
            'comment': 'Любая дополнительная информация о клиенте',
        }

    def clean_email(self):
        """
        Проверяем уникальность email адреса.

        При редактировании исключаем текущего клиента из проверки.
        """
        email = self.cleaned_data.get('email')

        if email:
            # Получаем queryset клиентов с таким email
            existing_clients = Client.objects.filter(email=email)

            # При редактировании исключаем текущего клиента
            if self.instance and self.instance.pk:
                existing_clients = existing_clients.exclude(pk=self.instance.pk)

            if existing_clients.exists():
                raise ValidationError(
                    'Клиент с таким email адресом уже существует.'
                )

        return email

    def clean_full_name(self):
        """Базовая валидация имени клиента."""
        full_name = self.cleaned_data.get('full_name')

        if full_name:
            # Проверяем минимальную длину
            if len(full_name.strip()) < 2:
                raise ValidationError(
                    'Имя должно содержать минимум 2 символа.'
                )

            # Убираем лишние пробелы
            full_name = ' '.join(full_name.split())

        return full_name


class MessageForm(forms.ModelForm):
    """
    Форма для создания и редактирования сообщений.

    Сообщения - это шаблоны писем, которые будут отправлены клиентам.
    Важно обеспечить, чтобы тема и содержание были информативными.
    """

    class Meta:
        model = Message
        fields = ['subject', 'body']

        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Краткое описание темы письма'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Основное содержание письма...'
            }),
        }

        labels = {
            'subject': 'Тема письма',
            'body': 'Содержание письма',
        }

        help_texts = {
            'subject': 'Краткое и понятное описание темы письма',
            'body': 'Основной текст, который получат ваши клиенты',
        }

    def clean_subject(self):
        """Валидация темы письма."""
        subject = self.cleaned_data.get('subject')

        if subject:
            subject = subject.strip()

            # Проверяем минимальную длину
            if len(subject) < 5:
                raise ValidationError(
                    'Тема письма должна содержать минимум 5 символов.'
                )

            # Проверяем максимальную длину
            if len(subject) > 200:
                raise ValidationError(
                    'Тема письма не должна превышать 200 символов.'
                )

        return subject

    def clean_body(self):
        """Валидация содержания письма."""
        body = self.cleaned_data.get('body')

        if body:
            body = body.strip()

            # Проверяем минимальную длину
            if len(body) < 10:
                raise ValidationError(
                    'Содержание письма должно содержать минимум 10 символов.'
                )

        return body


class MailingForm(forms.ModelForm):
    """
    Форма для создания и редактирования рассылок.

    Это самая сложная форма, поскольку рассылка объединяет
    сообщения, клиентов и временные параметры.
    """

    class Meta:
        model = Mailing
        fields = [
            'name', 'first_send_datetime', 'end_datetime',
            'message', 'clients', 'status'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название вашей рассылки'
            }),
            'first_send_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'message': forms.Select(attrs={
                'class': 'form-control'
            }),
            'clients': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

        labels = {
            'name': 'Название рассылки',
            'first_send_datetime': 'Дата и время первой отправки',
            'end_datetime': 'Дата и время окончания',
            'message': 'Сообщение для отправки',
            'clients': 'Получатели',
            'status': 'Статус рассылки',
        }

        help_texts = {
            'name': 'Описательное название для удобства управления',
            'first_send_datetime': 'Когда начать отправку рассылки',
            'end_datetime': 'Когда прекратить отправку рассылки',
            'message': 'Выберите сообщение из уже созданных',
            'clients': 'Выберите клиентов, которым отправить рассылку',
        }

    def __init__(self, *args, **kwargs):
        """
        Настраиваем форму для конкретного пользователя.

        Показываем только сообщения и клиентов текущего пользователя.
        """
        # Извлекаем пользователя из kwargs
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # Фильтруем сообщения по владельцу
            self.fields['message'].queryset = Message.objects.filter(owner=user)

            # Фильтруем клиентов по владельцу
            self.fields['clients'].queryset = Client.objects.filter(owner=user)

            # Если у пользователя нет сообщений, показываем подсказку
            if not self.fields['message'].queryset.exists():
                self.fields['message'].help_text = (
                    'Сначала создайте сообщение в разделе "Сообщения"'
                )
                self.fields['message'].widget.attrs['disabled'] = True

            # Если у пользователя нет клиентов, показываем подсказку
            if not self.fields['clients'].queryset.exists():
                self.fields['clients'].help_text = (
                    'Сначала добавьте клиентов в разделе "Клиенты"'
                )

    def clean_first_send_datetime(self):
        """Валидация даты первой отправки."""
        first_send_datetime = self.cleaned_data.get('first_send_datetime')

        if first_send_datetime:
            # Проверяем, что дата не в прошлом (при создании новой рассылки)
            if not self.instance.pk and first_send_datetime < timezone.now():
                raise ValidationError(
                    'Дата первой отправки не может быть в прошлом.'
                )

        return first_send_datetime

    def clean_end_datetime(self):
        """Валидация даты окончания."""
        end_datetime = self.cleaned_data.get('end_datetime')

        if end_datetime:
            # Проверяем, что дата окончания не в прошлом
            if end_datetime < timezone.now():
                raise ValidationError(
                    'Дата окончания не может быть в прошлом.'
                )

        return end_datetime

    def clean(self):
        """
        Общая валидация формы.

        Проверяем логические связи между полями.
        """
        cleaned_data = super().clean()
        first_send_datetime = cleaned_data.get('first_send_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        clients = cleaned_data.get('clients')
        message = cleaned_data.get('message')

        # Проверяем, что дата окончания после даты начала
        if first_send_datetime and end_datetime:
            if end_datetime <= first_send_datetime:
                raise ValidationError(
                    'Дата окончания должна быть позже даты первой отправки.'
                )

        # Проверяем, что выбрано хотя бы одно сообщение
        if not message:
            raise ValidationError(
                'Необходимо выбрать сообщение для отправки.'
            )

        # Проверяем, что выбран хотя бы один клиент
        if not clients or not clients.exists():
            raise ValidationError(
                'Необходимо выбрать хотя бы одного получателя.'
            )

        return cleaned_data


class MailingFilterForm(forms.Form):
    """
    Форма для фильтрации рассылок.

    Позволяет пользователям быстро находить нужные рассылки
    по различным критериям.
    """

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию...'
        }),
        label='Поиск'
    )

    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Все статусы')] + Mailing.STATUS_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Статус'
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Создано после'
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Создано до'
    )