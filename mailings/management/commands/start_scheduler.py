"""
Команда для запуска планировщика автоматических рассылок
"""

import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

logger = logging.getLogger(__name__)


@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """Удаляет старые записи выполнения заданий (старше 7 дней по умолчанию)"""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


@util.close_old_connections
def send_scheduled_mailings():
    """Функция для отправки запланированных рассылок"""
    from django.core.management import call_command

    logger.info("Запуск автоматической отправки рассылок")

    try:
        call_command('send_mailings', verbosity=1)
        logger.info("Автоматическая отправка рассылок завершена успешно")
    except Exception as e:
        logger.error(f"Ошибка при автоматической отправке рассылок: {e}")


class Command(BaseCommand):
    help = "Запускает планировщик для автоматической отправки рассылок"

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Добавляем задачу отправки рассылок каждую минуту
        scheduler.add_job(
            send_scheduled_mailings,
            trigger=CronTrigger(minute="*"),  # Каждую минуту
            id="send_mailings",
            max_instances=1,
            replace_existing=True,
        )

        # Добавляем задачу очистки старых записей каждый день в 02:00
        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(hour=2, minute=0),  # Каждый день в 02:00
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )

        try:
            logger.info("Запуск планировщика рассылок...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Остановка планировщика...")
            scheduler.shutdown()
            logger.info("Планировщик остановлен.")