"""
Команда для создания тестовых данных.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from mailings.models import Client, Message, Mailing
import random

User = get_user_model()


class Command(BaseCommand):
    """Команда для создания тестовых данных."""

    help = 'Создает тестовые данные для разработки и тестирования'

    def add_arguments(self, parser):
        """Добавляем аргументы командной строки."""
        parser.add_argument(
            '--users',
            type=int,
            default=3,
            help='Количество тестовых пользователей (по умолчанию: 3)',
        )
        parser.add_argument(
            '--clients',
            type=int,
            default=15,
            help='Количество тестовых клиентов (по умолчанию: 15)',
        )
        parser.add_argument(
            '--messages',
            type=int,
            default=8,
            help='Количество тестовых сообщений (по умолчанию: 8)',
        )
        parser.add_argument(
            '--mailings',
            type=int,
            default=5,
            help='Количество тестовых рассылок (по умолчанию: 5)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить существующие тестовые данные перед созданием новых',
        )

    def handle(self, *args, **options):
        """Основная логика команды."""

        users_count = options['users']
        clients_count = options['clients']
        messages_count = options['messages']
        mailings_count = options['mailings']
        clear_data = options['clear']

        if clear_data:
            self.clear_test_data()

        self.stdout.write('Создание тестовых данных...\n')

        # Создаем пользователей
        users = self.create_test_users(users_count)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Создано пользователей: {len(users)}')
        )

        # Создаем клиентов
        clients = self.create_test_clients(clients_count, users)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Создано клиентов: {len(clients)}')
        )

        # Создаем сообщения
        messages = self.create_test_messages(messages_count, users)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Создано сообщений: {len(messages)}')
        )

        # Создаем рассылки
        mailings = self.create_test_mailings(mailings_count, users, clients, messages)
        self.stdout.write(
            self.style.SUCCESS(f'✓ Создано рассылок: {len(mailings)}')
        )

        self.stdout.write(
            self.style.SUCCESS('\n🎉 Тестовые данные успешно созданы!')
        )

        # Выводим информацию для входа
        self.stdout.write('\n📋 Информация для входа в систему:')
        for user in users[:3]:  # Показываем первых 3 пользователей
            self.stdout.write(f'   Email: {user.email} | Пароль: testpass123')

    def clear_test_data(self):
        """Удаляет существующие тестовые данные."""
        self.stdout.write('Удаление существующих тестовых данных...')

        # Удаляем тестовых пользователей (и связанные данные удалятся каскадно)
        test_users = User.objects.filter(email__startswith='test')
        count = test_users.count()
        test_users.delete()

        self.stdout.write(f'Удалено тестовых записей: {count}')

    def create_test_users(self, count):
        """Создает тестовых пользователей."""
        users = []

        for i in range(1, count + 1):
            email = f'test{i}@example.com'

            # Проверяем, не существует ли уже такой пользователь
            if User.objects.filter(email=email).exists():
                continue

            user = User.objects.create_user(
                email=email,
                username=f'testuser{i}',
                password='testpass123',
                first_name=f'Тест{i}',
                last_name=f'Пользователь{i}',
                phone=f'+7 (999) 123-45-{i:02d}',
                country='Россия'
            )
            users.append(user)

        return users

    def create_test_clients(self, count, users):
        """Создает тестовых клиентов."""
        clients = []

        # Списки для генерации случайных имен
        first_names = [
            'Анна', 'Мария', 'Елена', 'Ольга', 'Светлана', 'Наталья', 'Ирина',
            'Александр', 'Сергей', 'Дмитрий', 'Андрей', 'Алексей', 'Михаил', 'Владимир'
        ]
        last_names = [
            'Иванова', 'Петрова', 'Сидорова', 'Козлова', 'Новикова', 'Морозова',
            'Иванов', 'Петров', 'Сидоров', 'Козлов', 'Новиков', 'Морозов'
        ]

        domains = ['gmail.com', 'yandex.ru', 'mail.ru', 'outlook.com', 'example.com']

        for i in range(1, count + 1):
            # Выбираем случайного пользователя как владельца
            owner = random.choice(users)

            # Генерируем случайное имя
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            full_name = f'{first_name} {last_name}'

            # Генерируем email
            username = f'{first_name.lower()}.{last_name.lower()}.{i}'
            domain = random.choice(domains)
            email = f'{username}@{domain}'

            # Проверяем уникальность email
            if Client.objects.filter(email=email).exists():
                email = f'client{i}@example.com'

            # Генерируем случайный комментарий
            comments = [
                'Активный подписчик',
                'VIP клиент',
                'Новый клиент',
                'Постоянный покупатель',
                'Заинтересован в акциях',
                '',  # Пустой комментарий
                'Предпочитает email рассылки',
                'Корпоративный клиент'
            ]

            client = Client.objects.create(
                email=email,
                full_name=full_name,
                comment=random.choice(comments),
                owner=owner
            )
            clients.append(client)

        return clients

    def create_test_messages(self, count, users):
        """Создает тестовые сообщения."""
        messages = []

        # Шаблоны сообщений
        message_templates = [
            {
                'subject': 'Добро пожаловать!',
                'body': 'Добро пожаловать в наш сервис! Мы рады видеть вас среди наших клиентов.'
            },
            {
                'subject': 'Специальное предложение',
                'body': 'У нас для вас специальное предложение! Скидка 20% на все товары до конца месяца.'
            },
            {
                'subject': 'Новости компании',
                'body': 'Ознакомьтесь с последними новостями нашей компании и предстоящими мероприятиями.'
            },
            {
                'subject': 'Напоминание о встрече',
                'body': 'Напоминаем вам о предстоящей встрече. Просим подтвердить ваше участие.'
            },
            {
                'subject': 'Обновление продукта',
                'body': 'Вышло обновление нашего продукта с новыми функциями и улучшениями.'
            },
            {
                'subject': 'Благодарность за покупку',
                'body': 'Спасибо за вашу покупку! Мы ценим ваше доверие и будем рады видеть вас снова.'
            },
            {
                'subject': 'Приглашение на вебинар',
                'body': 'Приглашаем вас на бесплатный вебинар по нашей тематике. Регистрация обязательна.'
            },
            {
                'subject': 'Поздравление с праздником',
                'body': 'Поздравляем вас с наступающими праздниками! Желаем здоровья и процветания.'
            }
        ]

        for i in range(count):
            # Выбираем случайного пользователя как владельца
            owner = random.choice(users)

            # Выбираем шаблон или создаем уникальный
            if i < len(message_templates):
                template = message_templates[i]
                subject = template['subject']
                body = template['body']
            else:
                subject = f'Тестовое сообщение #{i + 1}'
                body = f'Это тестовое сообщение номер {i + 1} для проверки функциональности системы рассылок.'

            message = Message.objects.create(
                subject=subject,
                body=body,
                owner=owner
            )
            messages.append(message)

        return messages

    def create_test_mailings(self, count, users, clients, messages):
        """Создает тестовые рассылки."""
        mailings = []

        for i in range(1, count + 1):
            # Выбираем случайного пользователя как владельца
            owner = random.choice(users)

            # Выбираем случайное сообщение владельца
            owner_messages = [msg for msg in messages if msg.owner == owner]
            if not owner_messages:
                # Если у пользователя нет сообщений, создаем одно
                message = Message.objects.create(
                    subject=f'Сообщение для рассылки {i}',
                    body=f'Содержание сообщения для рассылки {i}',
                    owner=owner
                )
            else:
                message = random.choice(owner_messages)

            # Генерируем даты
            now = timezone.now()

            # Случайные временные интервалы
            start_offset = random.randint(-7, 7)  # От -7 до +7 дней от сейчас
            duration = random.randint(1, 30)  # Длительность рассылки от 1 до 30 дней

            first_send = now + timedelta(days=start_offset)
            end_datetime = first_send + timedelta(days=duration)

            # Определяем статус на основе времени
            if first_send > now:
                status = Mailing.STATUS_CREATED
            elif end_datetime < now:
                status = Mailing.STATUS_COMPLETED
            else:
                status = random.choice([Mailing.STATUS_CREATED, Mailing.STATUS_STARTED])

            mailing = Mailing.objects.create(
                name=f'Тестовая рассылка #{i}',
                first_send_datetime=first_send,
                end_datetime=end_datetime,
                status=status,
                message=message,
                owner=owner
            )

            # Добавляем случайных клиентов владельца
            owner_clients = [client for client in clients if client.owner == owner]
            if owner_clients:
                # Выбираем от 1 до всех клиентов владельца
                selected_clients = random.sample(
                    owner_clients,
                    random.randint(1, min(len(owner_clients), 10))
                )
                mailing.clients.set(selected_clients)

            mailings.append(mailing)

        return mailings