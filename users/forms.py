"""
Формы для приложения пользователей.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


class UserRegistrationForm(UserCreationForm):
    """
    Форма для регистрации новых пользователей.

    Наследуемся от встроенной UserCreationForm, чтобы получить
    базовую функциональность (поля пароля, валидация), но расширяем
    ее для работы с нашей кастомной моделью пользователя.
    """

    # Дополнительные поля, которых нет в стандартной форме
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com'
        }),
        help_text='Обязательное поле. Будет использоваться для входа в систему.'
    )

    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваше имя'
        })
    )

    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваша фамилия'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        """
        Настраиваем внешний вид полей формы.

        Метод __init__ вызывается при создании формы.
        Здесь мы можем настроить виджеты (внешний вид полей)
        и добавить CSS-классы для красивого оформления.
        """
        super().__init__(*args, **kwargs)

        # Добавляем CSS-классы для всех полей
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        # Настраиваем placeholder'ы для полей паролей
        self.fields['password1'].widget.attrs['placeholder'] = 'Введите пароль'
        self.fields['password2'].widget.attrs['placeholder'] = 'Повторите пароль'

        # Настраиваем help_text для более понятных сообщений
        self.fields['password1'].help_text = (
            'Пароль должен содержать минимум 8 символов и не может быть '
            'слишком простым или похожим на ваши личные данные.'
        )

    def clean_email(self):
        """
        Дополнительная валидация email.

        Этот метод автоматически вызывается для поля email
        и позволяет добавить кастомные проверки.
        """
        email = self.cleaned_data.get('email')

        if email:
            # Проверяем, не существует ли уже пользователь с таким email
            if User.objects.filter(email=email).exists():
                raise ValidationError(
                    'Пользователь с таким email уже существует.'
                )

        return email

    def save(self, commit=True):
        """
        Переопределяем метод сохранения для работы с нашей моделью.

        Стандартная UserCreationForm не знает о нашем поле email,
        поэтому мы должны явно его обработать.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Используем email как username

        if commit:
            user.save()

        return user


class UserProfileForm(forms.ModelForm):
    """
    Форма для редактирования профиля пользователя.

    ModelForm автоматически создает поля формы на основе модели.
    Нам нужно только указать, какие поля включить и как их настроить.
    """

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'avatar', 'phone', 'country']

        # Настраиваем виджеты (внешний вид полей)
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваша фамилия'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@email.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Россия'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }

        # Настраиваем подписи полей
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'email': 'Email адрес',
            'avatar': 'Фотография профиля',
            'phone': 'Номер телефона',
            'country': 'Страна',
        }

        # Добавляем подсказки
        help_texts = {
            'email': 'Используется для входа в систему',
            'avatar': 'Загрузите изображение для вашего профиля',
            'phone': 'Укажите номер телефона для связи',
        }

    def clean_email(self):
        """
        Проверяем уникальность email при редактировании профиля.

        Важно исключить текущего пользователя из проверки,
        иначе он не сможет сохранить профиль без изменения email.
        """
        email = self.cleaned_data.get('email')

        if email:
            # Получаем queryset пользователей с таким email, исключая текущего
            existing_users = User.objects.filter(email=email)
            if self.instance:
                existing_users = existing_users.exclude(pk=self.instance.pk)

            if existing_users.exists():
                raise ValidationError(
                    'Пользователь с таким email уже существует.'
                )

        return email