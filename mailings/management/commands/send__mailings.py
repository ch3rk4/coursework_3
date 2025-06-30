"""
Команда для автоматической отправки рассылок по расписанию.
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from mailings.models import Mailing, MailingAttempt
from mailings.cache import invalidate_user_cache, invalidate_mailing_cache
import logging

# Настраиваем логирование
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Команда для автоматической отправки рассылок.

    Логика работы:
    1. Находим все рассылки со статусом "создана" или "запущена"
    2. Проверяем, что время отправки наступило
    3. Проверяем, что время окончания еще не прошло
    4. Отправляем письма всем клиентам рассылки
    5. Создаем записи о попытках отправки
    6. Обновляем статусы рассылок
    """

    help = 'Отправляет запланированные рассылки'

    def add_arguments(self, parser):
        """Добавляем аргументы командной строки."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать, что будет отправлено, но не отправлять',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод информации',
        )
        parser.add_argument(
            '--mailing-id',
            type=int,
            help='Отправить конкретную рассылку по ID',
        )

    def handle(self, *args, **options):
        """Основная логика команды."""

        verbosity = options.get('verbosity', 1)
        verbose = options.get('verbose', False) or verbosity > 1
        dry_run = options.get('dry_run', False)
        mailing_id = options.get('mailing_id')

        if dry_run:
            self.stdout.write(
                self.style.WARNING('РЕЖИМ ТЕСТИРОВАНИЯ - письма не будут отправлены')
            )

        current_time = timezone.now()

        # Определяем, какие рассылки обрабатывать
        if mailing_id:
            try:
                mailings = Mailing.objects.filter(id=mailing_id)
                if not mailings.exists():
                    self.stdout.write(
                        self.style.ERROR(f'Рассылка с ID {mailing_id} не найдена')
                    )
                    return
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('ID рассылки должен быть числом')
                )
                return
        else:
            # Находим рассылки для отправки
            mailings = Mailing.objects.filter(
                status__in=[Mailing.STATUS_CREATED, Mailing.STATUS_STARTED],
                first_send_datetime__lte=current_time,
                end_datetime__gt=current_time
            )

        if not mailings.exists():
            self.stdout.write('Нет рассылок для отправки в данный момент')
            return

        total_sent = 0
        total_failed = 0
        processed_mailings = 0

        for mailing in mailings:
            if verbose:
                self.stdout.write(f'\nОбработка рассылки: "{mailing.name}" (ID: {mailing.id})')

            # Проверяем, есть ли клиенты для отправки
            clients = mailing.clients.all()
            if not clients.exists():
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f'  ! У рассылки нет получателей')
                    )
                continue

            # Отправляем письма
            sent_count, failed_count = self.send_mailing_emails(
                mailing, clients, dry_run, verbose
            )

            total_sent += sent_count
            total_failed += failed_count
            processed_mailings += 1

            # Обновляем статус рассылки
            if not dry_run:
                if mailing.status == Mailing.STATUS_CREATED:
                    mailing.status = Mailing.STATUS_STARTED
                    mailing.save()
                    if verbose:
                        self.stdout.write(
                            f'  ✓ Статус рассылки изменен на "Запущена"'
                        )

                # Проверяем, не пора ли завершить рассылку
                if current_time >= mailing.end_datetime:
                    mailing.status = Mailing.STATUS_COMPLETED
                    mailing.save()
                    if verbose:
                        self.stdout.write(
                            f'  ✓ Статус рассылки изменен на "Завершена"'
                        )

                # Инвалидируем кеш
                invalidate_user_cache(mailing.owner.id)
                invalidate_mailing_cache(mailing.id)

        # Выводим итоговую статистику
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== ИТОГИ ОТПРАВКИ ===\n'
                f'Обработано рассылок: {processed_mailings}\n'
                f'Успешно отправлено: {total_sent}\n'
                f'Ошибок при отправке: {total_failed}'
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\nВНИМАНИЕ: Это был тестовый режим, письма не отправлялись!'
                )
            )

    def send_mailing_emails(self, mailing, clients, dry_run=False, verbose=False):
        """
        Отправляет письма всем клиентам рассылки.

        Args:
            mailing: Объект рассылки
            clients: QuerySet клиентов
            dry_run: Если True, письма не отправляются
            verbose: Подробный вывод

        Returns:
            tuple: (количество успешных отправок, количество ошибок)
        """
        sent_count = 0
        failed_count = 0

        if verbose:
            self.stdout.write(f'  Отправка {clients.count()} писем...')

        for client in clients:
            if verbose:
                self.stdout.write(f'    → {client.email}... ', ending='')

            if dry_run:
                # В режиме тестирования просто считаем успешными
                sent_count += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS('OK (тест)'))
                continue

            try:
                # Пытаемся отправить письмо
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[client.email],
                    fail_silently=False
                )

                # Создаем запись об успешной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    client_email=client.email,
                    status=MailingAttempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено'
                )

                sent_count += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS('OK'))

            except Exception as e:
                # Создаем запись о неуспешной попытке
                MailingAttempt.objects.create(
                    mailing=mailing,
                    client_email=client.email,
                    status=MailingAttempt.STATUS_FAILED,
                    server_response=str(e)
                )

                failed_count += 1
                if verbose:
                    self.stdout.write(self.style.ERROR(f'ОШИБКА: {e}'))

                # Логируем ошибку
                logger.error(
                    f'Ошибка отправки письма для рассылки {mailing.id} '
                    f'клиенту {client.email}: {e}'
                )

        return sent_count, failed_count