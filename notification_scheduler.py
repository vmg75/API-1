"""
Модуль для планирования и отправки уведомлений о погоде.
Обеспечивает автоматическую отправку погодных уведомлений по расписанию.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule

from user_manager import user_manager
from weather import get_weather_by_city, format_weather_data


class NotificationScheduler:
    """Класс для управления планировщиком уведомлений."""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Инициализация планировщика уведомлений.
        
        Args:
            cache_dir (str): Путь к папке с кэшем
        """
        self.cache_dir = cache_dir
        self.scheduled_file = os.path.join(cache_dir, "scheduled_notifications.json")
        self.bot_instance = None  # Будет установлен извне
        self.scheduler_thread = None
        self.is_running = False
        self._ensure_cache_dir()
        self._ensure_scheduled_file()
    
    def _ensure_cache_dir(self) -> None:
        """Создает папку cache если она не существует."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _ensure_scheduled_file(self) -> None:
        """Создает файл scheduled_notifications.json если он не существует."""
        if not os.path.exists(self.scheduled_file):
            with open(self.scheduled_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
    
    def set_bot_instance(self, bot):
        """
        Устанавливает экземпляр бота для отправки сообщений.
        
        Args:
            bot: Экземпляр Telegram бота
        """
        self.bot_instance = bot
    
    def load_scheduled_notifications(self) -> Dict:
        """
        Загружает расписание уведомлений из JSON файла.
        
        Returns:
            Dict: Словарь с расписанием уведомлений
        """
        try:
            with open(self.scheduled_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки расписания уведомлений: {e}")
            return {}
    
    def save_scheduled_notifications(self, scheduled_data: Dict) -> bool:
        """
        Сохраняет расписание уведомлений в JSON файл.
        
        Args:
            scheduled_data (Dict): Данные расписания для сохранения
            
        Returns:
            bool: True если сохранение прошло успешно
        """
        try:
            with open(self.scheduled_file, 'w', encoding='utf-8') as f:
                json.dump(scheduled_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения расписания уведомлений: {e}")
            return False
    
    def add_regular_notification(self, user_id: int, start_hour: int, end_hour: int, interval_hours: int) -> bool:
        """
        Добавляет регулярные уведомления в заданном диапазоне времени.
        
        Args:
            user_id (int): ID пользователя
            start_hour (int): Начальный час (0-23)
            end_hour (int): Конечный час (0-23)
            interval_hours (int): Интервал в часах
            
        Returns:
            bool: True если успешно добавлено
        """
        try:
            # Генерируем времена уведомлений
            notification_times = []
            current_hour = start_hour
            
            while current_hour <= end_hour:
                time_str = f"{current_hour:02d}:00"
                notification_times.append(time_str)
                current_hour += interval_hours
            
            # Обновляем настройки пользователя
            if user_manager.update_notification_settings(user_id, True, notification_times):
                # Перепланируем уведомления
                self.schedule_notifications()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Ошибка добавления регулярных уведомлений: {e}")
            return False

    def schedule_notifications(self) -> None:
        """
        Планирует уведомления для всех пользователей с включенными уведомлениями.
        """
        # Очищаем существующие задачи
        schedule.clear()
        
        # Получаем всех пользователей с уведомлениями
        users_with_notifications = user_manager.get_all_users_with_notifications()
        
        print(f"Планируем уведомления для {len(users_with_notifications)} пользователей")
        
        for user_info in users_with_notifications:
            user_id = user_info["user_id"]
            notification_times = user_info["notification_times"]
            
            for time_str in notification_times:
                try:
                    # Планируем задачу на указанное время
                    schedule.every().day.at(time_str).do(
                        self.send_weather_notification, 
                        user_id=user_id
                    ).tag(f"user_{user_id}_{time_str}")
                    print(f"Запланировано уведомление для пользователя {user_id} на {time_str}")
                except Exception as e:
                    print(f"Ошибка планирования уведомления для пользователя {user_id} на {time_str}: {e}")
    
    def send_weather_notification(self, user_id: int) -> None:
        """
        Отправляет уведомление о погоде пользователю.
        
        Args:
            user_id (int): ID пользователя в Telegram
        """
        if not self.bot_instance:
            print("Бот не инициализирован для отправки уведомлений")
            return
        
        try:
            # Получаем город пользователя
            city = user_manager.get_user_city(user_id)
            if not city:
                print(f"Город не установлен для пользователя {user_id}")
                return
            
            # Получаем данные о погоде
            weather_data = get_weather_by_city(city)
            if "error" in weather_data:
                message = f"❌ Не удалось получить погоду для города {city}: {weather_data['error']}"
            else:
                formatted_weather = format_weather_data(weather_data)
                message = f"🌅 Утренний прогноз погоды\n\n{formatted_weather}"
            
            # Отправляем сообщение
            self.bot_instance.send_message(user_id, message)
            print(f"Отправлено уведомление пользователю {user_id} о погоде в {city}")
            
            # Обновляем время последней активности
            user_manager.update_last_activity(user_id)
            
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
    
    def start_scheduler(self) -> None:
        """
        Запускает планировщик уведомлений в отдельном потоке.
        """
        if self.is_running:
            print("Планировщик уже запущен")
            return
        
        self.is_running = True
        
        def run_scheduler():
            while self.is_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Проверяем каждую минуту
                except Exception as e:
                    print(f"Ошибка в планировщике: {e}")
                    time.sleep(60)
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Планируем уведомления
        self.schedule_notifications()
        
        print("Планировщик уведомлений запущен")
    
    def stop_scheduler(self) -> None:
        """
        Останавливает планировщик уведомлений.
        """
        self.is_running = False
        schedule.clear()
        print("Планировщик уведомлений остановлен")
    
    def add_user_notification(self, user_id: int, times: List[str]) -> bool:
        """
        Добавляет уведомления для конкретного пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            times (List[str]): Времена уведомлений в формате "HH:MM"
            
        Returns:
            bool: True если уведомления добавлены успешно
        """
        try:
            for time_str in times:
                schedule.every().day.at(time_str).do(
                    self.send_weather_notification, 
                    user_id=user_id
                ).tag(f"user_{user_id}_{time_str}")
            
            print(f"Добавлены уведомления для пользователя {user_id} на времена: {times}")
            return True
        except Exception as e:
            print(f"Ошибка добавления уведомлений для пользователя {user_id}: {e}")
            return False
    
    def remove_user_notifications(self, user_id: int) -> bool:
        """
        Удаляет все уведомления для конкретного пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если уведомления удалены успешно
        """
        try:
            # Получаем все задачи с тегом пользователя
            jobs_to_remove = []
            for job in schedule.jobs:
                if f"user_{user_id}_" in str(job.tags):
                    jobs_to_remove.append(job)
            
            # Удаляем задачи
            for job in jobs_to_remove:
                schedule.cancel_job(job)
            
            print(f"Удалены уведомления для пользователя {user_id}")
            return True
        except Exception as e:
            print(f"Ошибка удаления уведомлений для пользователя {user_id}: {e}")
            return False
    
    def get_scheduled_jobs_info(self) -> List[Dict]:
        """
        Получает информацию о запланированных задачах.
        
        Returns:
            List[Dict]: Список информации о задачах
        """
        jobs_info = []
        for job in schedule.jobs:
            jobs_info.append({
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit,
                "tags": list(job.tags) if job.tags else []
            })
        return jobs_info
    
    def reschedule_user_notifications(self, user_id: int) -> bool:
        """
        Перепланирует уведомления для пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если перепланирование прошло успешно
        """
        try:
            # Удаляем старые уведомления
            self.remove_user_notifications(user_id)
            
            # Получаем новые настройки пользователя
            user_data = user_manager.get_user_data(user_id)
            if not user_data or not user_data.get("notifications_enabled", False):
                return True
            
            notification_times = user_data.get("notification_times", [])
            
            # Добавляем новые уведомления
            return self.add_user_notification(user_id, notification_times)
            
        except Exception as e:
            print(f"Ошибка перепланирования уведомлений для пользователя {user_id}: {e}")
            return False


# Создаем глобальный экземпляр планировщика
notification_scheduler = NotificationScheduler()


# Тестовые функции
if __name__ == "__main__":
    print("Тестирование NotificationScheduler...")
    
    # Тестируем загрузку и сохранение расписания
    scheduler = NotificationScheduler()
    
    # Тестовые данные
    test_schedule = {
        "user_123456789": {
            "times": ["08:00", "18:00"],
            "enabled": True,
            "last_sent": None
        }
    }
    
    print(f"Сохранение тестового расписания: {scheduler.save_scheduled_notifications(test_schedule)}")
    print(f"Загрузка расписания: {scheduler.load_scheduled_notifications()}")
    
    # Тестируем получение информации о задачах
    jobs_info = scheduler.get_scheduled_jobs_info()
    print(f"Информация о задачах: {jobs_info}")
    
    print("Тестирование завершено!")
