"""
Модуль для управления пользовательскими данными в JSON формате.
Обеспечивает загрузку, сохранение и обновление настроек пользователей.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List


class UserManager:
    """Класс для управления пользовательскими данными."""
    
    def __init__(self, cache_dir: str = "cache"):
        """
        Инициализация менеджера пользователей.
        
        Args:
            cache_dir (str): Путь к папке с кэшем
        """
        self.cache_dir = cache_dir
        self.users_file = os.path.join(cache_dir, "users.json")
        self._ensure_cache_dir()
        self._ensure_users_file()
    
    def _ensure_cache_dir(self) -> None:
        """Создает папку cache если она не существует."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _ensure_users_file(self) -> None:
        """Создает файл users.json если он не существует."""
        if not os.path.exists(self.users_file):
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
    
    def load_users(self) -> Dict:
        """
        Загружает данные всех пользователей из JSON файла.
        
        Returns:
            Dict: Словарь с данными пользователей
        """
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка загрузки пользователей: {e}")
            return {}
    
    def save_users(self, users_data: Dict) -> bool:
        """
        Сохраняет данные пользователей в JSON файл.
        
        Args:
            users_data (Dict): Данные пользователей для сохранения
            
        Returns:
            bool: True если сохранение прошло успешно
        """
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения пользователей: {e}")
            return False
    
    def get_user_data(self, user_id: int) -> Optional[Dict]:
        """
        Получает данные конкретного пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            Optional[Dict]: Данные пользователя или None если не найден
        """
        users = self.load_users()
        return users.get(str(user_id))
    
    def add_user(self, user_id: int, default_city: str = "Москва") -> bool:
        """
        Добавляет нового пользователя с настройками по умолчанию.
        
        Args:
            user_id (int): ID пользователя в Telegram
            default_city (str): Город по умолчанию
            
        Returns:
            bool: True если пользователь добавлен успешно
        """
        users = self.load_users()
        
        # Проверяем, не существует ли уже пользователь
        if str(user_id) in users:
            return False
        
        # Создаем данные нового пользователя
        users[str(user_id)] = {
            "default_city": default_city,
            "notifications_enabled": False,
            "notification_times": ["08:00", "18:00"],
            "language": "ru",
            "last_activity": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        
        return self.save_users(users)
    
    def update_user_city(self, user_id: int, city: str, latitude: float = None, longitude: float = None) -> bool:
        """
        Обновляет город по умолчанию для пользователя с координатами.
        
        Args:
            user_id (int): ID пользователя в Telegram
            city (str): Новый город по умолчанию
            latitude (float, optional): Широта города
            longitude (float, optional): Долгота города
            
        Returns:
            bool: True если обновление прошло успешно
        """
        users = self.load_users()
        
        if str(user_id) not in users:
            return False
        
        users[str(user_id)]["default_city"] = city
        users[str(user_id)]["last_activity"] = datetime.now().isoformat()
        
        # Сохраняем координаты если они предоставлены
        if latitude is not None and longitude is not None:
            users[str(user_id)]["city_latitude"] = latitude
            users[str(user_id)]["city_longitude"] = longitude
        
        return self.save_users(users)
    
    def update_notification_settings(self, user_id: int, enabled: bool, times: List[str] = None) -> bool:
        """
        Обновляет настройки уведомлений для пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            enabled (bool): Включены ли уведомления
            times (List[str]): Времена отправки уведомлений в формате "HH:MM"
            
        Returns:
            bool: True если обновление прошло успешно
        """
        users = self.load_users()
        
        if str(user_id) not in users:
            return False
        
        users[str(user_id)]["notifications_enabled"] = enabled
        if times is not None:
            users[str(user_id)]["notification_times"] = times
        users[str(user_id)]["last_activity"] = datetime.now().isoformat()
        
        return self.save_users(users)
    
    def update_last_activity(self, user_id: int) -> bool:
        """
        Обновляет время последней активности пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если обновление прошло успешно
        """
        users = self.load_users()
        
        if str(user_id) not in users:
            return False
        
        users[str(user_id)]["last_activity"] = datetime.now().isoformat()
        
        return self.save_users(users)
    
    def get_user_city(self, user_id: int) -> Optional[str]:
        """
        Получает город по умолчанию для пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            Optional[str]: Город по умолчанию или None
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("default_city") if user_data else None
    
    def get_user_coordinates(self, user_id: int) -> Optional[tuple]:
        """
        Получает координаты города пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            Optional[tuple]: Кортеж (latitude, longitude) или None
        """
        user_data = self.get_user_data(user_id)
        if user_data and "city_latitude" in user_data and "city_longitude" in user_data:
            return (user_data["city_latitude"], user_data["city_longitude"])
        return None
    
    def has_user_coordinates(self, user_id: int) -> bool:
        """
        Проверяет, есть ли у пользователя сохраненные координаты города.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если координаты есть
        """
        return self.get_user_coordinates(user_id) is not None
    
    def is_notifications_enabled(self, user_id: int) -> bool:
        """
        Проверяет, включены ли уведомления для пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если уведомления включены
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("notifications_enabled", False) if user_data else False
    
    def get_notification_times(self, user_id: int) -> List[str]:
        """
        Получает времена уведомлений для пользователя.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            List[str]: Список времен уведомлений
        """
        user_data = self.get_user_data(user_id)
        return user_data.get("notification_times", ["08:00", "18:00"]) if user_data else ["08:00", "18:00"]
    
    def get_all_users_with_notifications(self) -> List[Dict]:
        """
        Получает всех пользователей с включенными уведомлениями.
        
        Returns:
            List[Dict]: Список пользователей с уведомлениями
        """
        users = self.load_users()
        users_with_notifications = []
        
        for user_id, user_data in users.items():
            if user_data.get("notifications_enabled", False):
                users_with_notifications.append({
                    "user_id": int(user_id),
                    "default_city": user_data.get("default_city", "Москва"),
                    "notification_times": user_data.get("notification_times", ["08:00", "18:00"])
                })
        
        return users_with_notifications
    
    def delete_user(self, user_id: int) -> bool:
        """
        Удаляет пользователя из системы.
        
        Args:
            user_id (int): ID пользователя в Telegram
            
        Returns:
            bool: True если пользователь удален успешно
        """
        users = self.load_users()
        
        if str(user_id) not in users:
            return False
        
        del users[str(user_id)]
        return self.save_users(users)


# Создаем глобальный экземпляр менеджера пользователей
user_manager = UserManager()


# Тестовые функции
if __name__ == "__main__":
    # Тестирование функций
    test_user_id = 123456789
    
    print("Тестирование UserManager...")
    
    # Добавляем тестового пользователя
    print(f"Добавление пользователя {test_user_id}: {user_manager.add_user(test_user_id, 'Санкт-Петербург')}")
    
    # Получаем данные пользователя
    user_data = user_manager.get_user_data(test_user_id)
    print(f"Данные пользователя: {user_data}")
    
    # Обновляем город
    print(f"Обновление города: {user_manager.update_user_city(test_user_id, 'Казань')}")
    
    # Включаем уведомления
    print(f"Включение уведомлений: {user_manager.update_notification_settings(test_user_id, True, ['09:00', '21:00'])}")
    
    # Получаем обновленные данные
    updated_data = user_manager.get_user_data(test_user_id)
    print(f"Обновленные данные: {updated_data}")
    
    # Получаем пользователей с уведомлениями
    users_with_notifications = user_manager.get_all_users_with_notifications()
    print(f"Пользователи с уведомлениями: {users_with_notifications}")
    
    # Удаляем тестового пользователя
    print(f"Удаление пользователя: {user_manager.delete_user(test_user_id)}")
    
    print("Тестирование завершено!")
