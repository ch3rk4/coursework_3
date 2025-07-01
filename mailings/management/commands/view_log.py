"""
Команда для просмотра и анализа логов приложения.
"""

import json
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """Команда для просмотра и анализа логов."""

    help = "Просмотр и анализ логов приложения"

    def add_arguments(self, parser):
        """Добавляем аргументы командной строки."""
        parser.add_argument(
            "--last",
            type=int,
            default=50,
            help="Количество последних записей для показа (по умолчанию: 50)",
        )
        parser.add_argument(
            "--level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Фильтр по уровню логирования",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Фильтр по ID пользователя",
        )
        parser.add_argument(
            "--mailing-id",
            type=int,
            help="Фильтр по ID рассылки",
        )
        parser.add_argument(
            "--date",
            help="Фильтр по дате (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Показать статистику логов",
        )
        parser.add_argument(
            "--errors",
            action="store_true",
            help="Показать только ошибки",
        )
        parser.add_argument(
            "--follow",
            action="store_true",
            help="Следить за логами в реальном времени",
        )

    def handle(self, *args, **options):
        """Основная логика команды."""

        if options["stats"]:
            self.show_stats()
            return

        if options["errors"]:
            options["level"] = "ERROR"

        if options["follow"]:
            self.follow_logs(options)
        else:
            self.show_logs(options)

    def show_logs(self, options):
        """Показывает логи согласно фильтрам."""

        log_files = self.get_log_files()

        if not log_files:
            self.stdout.write(self.style.WARNING("Файлы логов не найдены"))
            return

        # Собираем все записи логов
        all_logs = []
        for log_file in log_files:
            logs = self.read_log_file(log_file, options)
            all_logs.extend(logs)

        # Сортируем по времени
        all_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Применяем лимит
        limited_logs = all_logs[: options["last"]]

        if not limited_logs:
            self.stdout.write(
                self.style.WARNING("Логи не найдены по указанным критериям")
            )
            return

        # Отображаем логи
        self.display_logs(limited_logs)

    def read_log_file(self, file_path, options):
        """Читает и фильтрует логи из файла."""

        logs = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Пытаемся парсить как JSON (структурированные логи)
                        log_entry = json.loads(line)
                    except json.JSONDecodeError:
                        # Если не JSON, создаем простую структуру
                        log_entry = {
                            "timestamp": datetime.now().isoformat(),
                            "level": "INFO",
                            "message": line,
                            "raw": True,
                        }

                    # Применяем фильтры
                    if self.matches_filters(log_entry, options):
                        logs.append(log_entry)

        except FileNotFoundError:
            pass
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка чтения файла {file_path}: {e}"))

        return logs

    def matches_filters(self, log_entry, options):
        """Проверяет, соответствует ли запись фильтрам."""

        # Фильтр по уровню
        if options["level"] and log_entry.get("level") != options["level"]:
            return False

        # Фильтр по пользователю
        if options["user_id"] and log_entry.get("user_id") != options["user_id"]:
            return False

        # Фильтр по рассылке
        if (
            options["mailing_id"]
            and log_entry.get("mailing_id") != options["mailing_id"]
        ):
            return False

        # Фильтр по дате
        if options["date"]:
            try:
                log_date = datetime.fromisoformat(log_entry.get("timestamp", ""))
                filter_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
                if log_date.date() != filter_date:
                    return False
            except (ValueError, TypeError):
                pass

        return True

    def display_logs(self, logs):
        """Отображает логи в удобном формате."""

        self.stdout.write(self.style.SUCCESS(f"\n=== ЛОГИ ({len(logs)} записей) ===\n"))

        for log in logs:
            # Определяем цвет по уровню
            level = log.get("level", "INFO")
            if level == "ERROR" or level == "CRITICAL":
                level_style = self.style.ERROR
            elif level == "WARNING":
                level_style = self.style.WARNING
            elif level == "SUCCESS":
                level_style = self.style.SUCCESS
            else:
                level_style = self.style.HTTP_INFO

            # Форматируем время
            timestamp = log.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = timestamp

            # Основная информация
            self.stdout.write(
                f"{formatted_time} | {level_style(level.ljust(8))} | {log.get('message', '')}"
            )

            # Дополнительная информация
            if log.get("user_id"):
                self.stdout.write(
                    f"  👤 Пользователь: {log.get('user_email', log['user_id'])}"
                )

            if log.get("mailing_id"):
                self.stdout.write(f"  📧 Рассылка: {log['mailing_id']}")

            if log.get("ip_address"):
                self.stdout.write(f"  🌐 IP: {log['ip_address']}")

            if log.get("extra_data"):
                extra = log["extra_data"]
                if isinstance(extra, dict):
                    for key, value in extra.items():
                        if key not in [
                            "duration_seconds"
                        ]:  # Пропускаем техническую информацию
                            self.stdout.write(f"  ℹ️  {key}: {value}")

            if log.get("exception"):
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Исключение: {log['exception']}")
                )

            self.stdout.write("")  # Пустая строка для разделения

    def show_stats(self):
        """Показывает статистику логов."""

        self.stdout.write(self.style.SUCCESS("\n=== СТАТИСТИКА ЛОГОВ ===\n"))

        log_files = self.get_log_files()

        if not log_files:
            self.stdout.write(self.style.WARNING("Файлы логов не найдены"))
            return

        total_logs = 0
        level_stats = {}
        user_stats = {}
        daily_stats = {}

        for log_file in log_files:
            file_stats = self.analyze_log_file(log_file)
            total_logs += file_stats["total"]

            # Суммируем статистику по уровням
            for level, count in file_stats["levels"].items():
                level_stats[level] = level_stats.get(level, 0) + count

            # Суммируем статистику по пользователям
            for user, count in file_stats["users"].items():
                user_stats[user] = user_stats.get(user, 0) + count

            # Суммируем ежедневную статистику
            for date, count in file_stats["daily"].items():
                daily_stats[date] = daily_stats.get(date, 0) + count

        # Отображаем статистику
        self.stdout.write(f"📊 Общее количество записей: {total_logs}")
        self.stdout.write("")

        # Статистика по уровням
        self.stdout.write("📈 По уровням логирования:")
        for level, count in sorted(level_stats.items()):
            percentage = (count / total_logs * 100) if total_logs > 0 else 0
            self.stdout.write(f"  {level}: {count} ({percentage:.1f}%)")
        self.stdout.write("")

        # Топ пользователей
        if user_stats:
            self.stdout.write("👥 Топ активных пользователей:")
            sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
            for user, count in sorted_users[:10]:
                self.stdout.write(f"  {user}: {count} событий")
            self.stdout.write("")

        # Активность по дням
        if daily_stats:
            self.stdout.write("📅 Активность за последние дни:")
            sorted_days = sorted(daily_stats.items(), reverse=True)
            for date, count in sorted_days[:7]:
                self.stdout.write(f"  {date}: {count} событий")

    def analyze_log_file(self, file_path):
        """Анализирует один файл логов."""

        stats = {"total": 0, "levels": {}, "users": {}, "daily": {}}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    stats["total"] += 1

                    try:
                        log_entry = json.loads(line)

                        # Статистика по уровням
                        level = log_entry.get("level", "UNKNOWN")
                        stats["levels"][level] = stats["levels"].get(level, 0) + 1

                        # Статистика по пользователям
                        user_email = log_entry.get("user_email")
                        if user_email:
                            stats["users"][user_email] = (
                                stats["users"].get(user_email, 0) + 1
                            )

                        # Ежедневная статистика
                        timestamp = log_entry.get("timestamp")
                        if timestamp:
                            try:
                                dt = datetime.fromisoformat(
                                    timestamp.replace("Z", "+00:00")
                                )
                                date_key = dt.strftime("%Y-%m-%d")
                                stats["daily"][date_key] = (
                                    stats["daily"].get(date_key, 0) + 1
                                )
                            except:
                                pass

                    except json.JSONDecodeError:
                        # Не JSON логи
                        stats["levels"]["UNKNOWN"] = (
                            stats["levels"].get("UNKNOWN", 0) + 1
                        )

        except FileNotFoundError:
            pass
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Ошибка анализа файла {file_path}: {e}")
            )

        return stats

    def get_log_files(self):
        """Возвращает список файлов логов."""

        logs_dir = settings.BASE_DIR / "logs"

        if not os.path.exists(logs_dir):
            return []

        log_files = []
        for filename in os.listdir(logs_dir):
            if filename.endswith(".log"):
                log_files.append(logs_dir / filename)

        return sorted(log_files)

    def follow_logs(self, options):
        """Следит за логами в реальном времени."""

        self.stdout.write(
            self.style.SUCCESS("Слежение за логами... (Ctrl+C для остановки)")
        )

        # Простая реализация tail -f для логов
        import time

        log_files = self.get_log_files()
        if not log_files:
            self.stdout.write(self.style.WARNING("Файлы логов не найдены"))
            return

        # Запоминаем последние позиции в файлах
        file_positions = {}
        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    f.seek(0, 2)  # Переходим в конец файла
                    file_positions[log_file] = f.tell()
            except:
                file_positions[log_file] = 0

        try:
            while True:
                new_logs = []

                for log_file in log_files:
                    try:
                        with open(log_file, "r") as f:
                            f.seek(file_positions[log_file])
                            new_lines = f.readlines()
                            file_positions[log_file] = f.tell()

                            for line in new_lines:
                                line = line.strip()
                                if line:
                                    try:
                                        log_entry = json.loads(line)
                                        if self.matches_filters(log_entry, options):
                                            new_logs.append(log_entry)
                                    except json.JSONDecodeError:
                                        if not options.get(
                                            "level"
                                        ):  # Показываем неструктурированные логи только если нет фильтра по уровню
                                            new_logs.append(
                                                {
                                                    "timestamp": datetime.now().isoformat(),
                                                    "level": "INFO",
                                                    "message": line,
                                                    "raw": True,
                                                }
                                            )
                    except:
                        pass

                if new_logs:
                    new_logs.sort(key=lambda x: x.get("timestamp", ""))
                    self.display_logs(new_logs)

                time.sleep(1)  # Проверяем каждую секунду

        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nСлежение за логами остановлено"))
