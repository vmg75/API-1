"""
Телеграм бот для получения информации о погоде.
Поддерживает команды для получения текущей погоды, прогнозов и настройки уведомлений.
"""

import telebot
from telebot import types
from dotenv import load_dotenv
import os
import logging
import signal
import sys
from datetime import datetime

# Импортируем наши модули
from user_manager import user_manager
from notification_scheduler import notification_scheduler
from weather import (
    get_weather_by_city, 
    get_hourly_weather_by_city, 
    get_air_pollution_by_city,
    get_daily_weather_by_city,
    get_cities_list,
    get_weather_by_coordinates,
    get_hourly_weather,
    get_daily_weather,
    get_air_pollution,
    get_city_by_coordinates,
    format_weather_data, 
    format_hourly_weather, 
    format_daily_weather,
    analyze_air_pollution,
    COUNT_DAILY_FORECAST,
    COUNT_3_HOURS_FORECAST
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ Ошибка: API ключ telegram не найден!")
    print("Создайте файл .env в корне проекта и добавьте:")
    print("TELEGRAM_BOT_TOKEN=ваш_токен_бота")
    sys.exit(1)

# Создаем экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

# Устанавливаем бот для планировщика уведомлений
notification_scheduler.set_bot_instance(bot)

# Временное хранилище для выбора города
city_selection_data = {}


def create_main_keyboard():
    """Создает основную клавиатуру с кнопками."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    weather_btn = types.InlineKeyboardButton("🌤️ Текущая погода", callback_data="weather_current")
    forecast_btn = types.InlineKeyboardButton("📅 Прогноз", callback_data="weather_daily")
    hourly_btn = types.InlineKeyboardButton("⏰ Почасовой", callback_data="weather_hourly")
    air_btn = types.InlineKeyboardButton("🌬️ Воздух", callback_data="weather_air")
    settings_btn = types.InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
    help_btn = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    
    keyboard.add(weather_btn, forecast_btn)
    keyboard.add(hourly_btn, air_btn)
    keyboard.add(settings_btn, help_btn)
    
    return keyboard


def create_settings_keyboard():
    """Создает клавиатуру настроек."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    city_btn = types.InlineKeyboardButton("🏙️ Изменить город", callback_data="change_city")
    notifications_btn = types.InlineKeyboardButton("🔔 Настройки уведомлений", callback_data="notification_settings")
    frequency_btn = types.InlineKeyboardButton("⏰ Настроить частоту", callback_data="frequency_settings")
    forecast_count_btn = types.InlineKeyboardButton("📊 Настройки прогноза", callback_data="forecast_settings")
    back_btn = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")
    
    keyboard.add(city_btn, notifications_btn, frequency_btn, forecast_count_btn, back_btn)
    
    return keyboard


def create_city_setting_keyboard():
    """Создает клавиатуру для выбора способа установки города."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопки для выбора способа установки города
    manual_btn = types.InlineKeyboardButton("✏️ Ввести вручную", callback_data="city_manual")
    auto_btn = types.InlineKeyboardButton("📍 Получить автоматически", callback_data="city_auto")
    
    keyboard.add(manual_btn, auto_btn)
    
    # Кнопка назад
    back_btn = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    keyboard.add(back_btn)
    
    return keyboard


def create_frequency_settings_keyboard():
    """Создает клавиатуру настроек частоты уведомлений."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    # Кнопки для выбора типа частоты
    fixed_time_btn = types.InlineKeyboardButton("🕐 Заданное время", callback_data="frequency_fixed_time")
    interval_btn = types.InlineKeyboardButton("⏱️ Каждые Х часов", callback_data="frequency_interval")
    
    keyboard.add(fixed_time_btn, interval_btn)
    
    # Кнопка назад
    back_btn = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    keyboard.add(back_btn)
    
    return keyboard


def create_forecast_settings_keyboard():
    """Создает клавиатуру настроек прогноза."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    # Кнопки для выбора количества прогнозов
    count_8_btn = types.InlineKeyboardButton("8 (24ч)", callback_data="forecast_count_8")
    count_16_btn = types.InlineKeyboardButton("16 (48ч)", callback_data="forecast_count_16")
    count_24_btn = types.InlineKeyboardButton("24 (72ч)", callback_data="forecast_count_24")
    count_40_btn = types.InlineKeyboardButton("40 (120ч)", callback_data="forecast_count_40")
    
    keyboard.add(count_8_btn, count_16_btn, count_24_btn, count_40_btn)
    
    # Кнопка назад
    back_btn = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    keyboard.add(back_btn)
    
    return keyboard


def create_city_selection_keyboard(cities_data):
    """Создает клавиатуру для выбора города из списка."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for i, city_info in enumerate(cities_data["cities"]):
        button_text = f"{i+1}. {city_info['display_name']}"
        callback_data = f"select_city_{i}"
        button = types.InlineKeyboardButton(button_text, callback_data=callback_data)
        keyboard.add(button)
    
    # Добавляем кнопку отмены
    cancel_btn = types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_city_selection")
    keyboard.add(cancel_btn)
    
    return keyboard


def create_notification_keyboard(user_id):
    """Создает клавиатуру настроек уведомлений."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    user_data = user_manager.get_user_data(user_id)
    notifications_enabled = user_data.get("notifications_enabled", False) if user_data else False
    
    toggle_text = "🔕 Выключить уведомления" if notifications_enabled else "🔔 Включить уведомления"
    toggle_btn = types.InlineKeyboardButton(toggle_text, callback_data="toggle_notifications")
    
    times_btn = types.InlineKeyboardButton("⏰ Изменить интервал уведомлений", callback_data="change_notification_times")
    back_btn = types.InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="settings")
    
    keyboard.add(toggle_btn, times_btn, back_btn)
    
    return keyboard


def ensure_user_exists(user_id):
    """Убеждается, что пользователь существует в системе."""
    if not user_manager.get_user_data(user_id):
        user_manager.add_user(user_id)
        logger.info(f"Добавлен новый пользователь: {user_id}")


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    welcome_text = f"""
🌤️ Добро пожаловать в Weather Bot!

Привет, {message.from_user.first_name}! 

Я помогу вам узнать актуальную информацию о погоде в любом городе мира.

📋 Доступные функции:
• Текущая погода
• Прогноз на {COUNT_DAILY_FORECAST} дней
• Почасовой прогноз {COUNT_3_HOURS_FORECAST} часов
• Качество воздуха
• Настройка уведомлений

Выберите действие с помощью кнопок ниже:
"""
    
    bot.send_message(
        user_id, 
        welcome_text, 
        reply_markup=create_main_keyboard()
    )
    
    user_manager.update_last_activity(user_id)


@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработчик команды /help."""
    help_text = f"""
❓ Справка по командам:

/start - Главное меню
/weather [город] - Текущая погода
/forecast [город] - Прогноз на {COUNT_DAILY_FORECAST} дней  
/hourly [город] - Почасовой прогноз {COUNT_3_HOURS_FORECAST} часов
/air [город] - Качество воздуха
/setcity [город] - Установить город по умолчанию
/notifications - Настройки уведомлений
/help - Эта справка

💡 Совет: Если не указать город, будет использован ваш город по умолчанию.

🔔 Уведомления: Вы можете настроить автоматические уведомления о погоде в удобное время.
"""
    
    bot.send_message(message.from_user.id, help_text)


@bot.message_handler(commands=['weather'])
def handle_weather_command(message):
    """Обработчик команды /weather."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    # Извлекаем город из команды
    command_parts = message.text.split(' ', 1)
    city = command_parts[1] if len(command_parts) > 1 else None
    
    if not city:
        city = user_manager.get_user_city(user_id)
        if not city:
            bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
            return
    
    handle_city_search(user_id, city, "current")


@bot.message_handler(commands=['forecast'])
def handle_forecast_command(message):
    """Обработчик команды /forecast."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    command_parts = message.text.split(' ', 1)
    city = command_parts[1] if len(command_parts) > 1 else None
    
    if not city:
        city = user_manager.get_user_city(user_id)
        if not city:
            bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
            return
    
    handle_city_search(user_id, city, "forecast")


@bot.message_handler(commands=['hourly'])
def handle_hourly_command(message):
    """Обработчик команды /hourly."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    command_parts = message.text.split(' ', 1)
    city = command_parts[1] if len(command_parts) > 1 else None
    
    if not city:
        city = user_manager.get_user_city(user_id)
        if not city:
            bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
            return
    
    handle_city_search(user_id, city, "hourly")


@bot.message_handler(commands=['air'])
def handle_air_command(message):
    """Обработчик команды /air."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    command_parts = message.text.split(' ', 1)
    city = command_parts[1] if len(command_parts) > 1 else None
    
    if not city:
        city = user_manager.get_user_city(user_id)
        if not city:
            bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
            return
    
    handle_city_search(user_id, city, "air")


@bot.message_handler(commands=['setcity'])
def handle_setcity_command(message):
    """Обработчик команды /setcity."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    command_parts = message.text.split(' ', 1)
    if len(command_parts) < 2:
        bot.send_message(user_id, "❌ Укажите город. Пример: /setcity Москва")
        return
    
    city = command_parts[1].strip()
    
    # Используем поиск города для выбора
    city_selection_data[user_id] = {
        "city_query": city,
        "weather_type": "set_city",  # Специальный тип для установки города
        "cities": []
    }
    
    handle_city_search(user_id, city, "set_city")


@bot.message_handler(commands=['notifications'])
def handle_notifications_command(message):
    """Обработчик команды /notifications."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    user_data = user_manager.get_user_data(user_id)
    notifications_enabled = user_data.get("notifications_enabled", False)
    notification_times = user_data.get("notification_times", ["08:00", "18:00"])
    
    status_text = "включены" if notifications_enabled else "выключены"
    times_text = ", ".join(notification_times)
    
    text = f"""
🔔 Настройки уведомлений:

Статус: {status_text}
Время отправки: {times_text}

Используйте кнопки ниже для изменения настроек:
"""
    
    bot.send_message(
        user_id, 
        text, 
        reply_markup=create_notification_keyboard(user_id)
    )


@bot.message_handler(commands=['regular'])
def handle_regular_command(message):
    """Обработчик команды /regular для настройки регулярных уведомлений."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    command_parts = message.text.split()
    
    if len(command_parts) != 4:
        help_text = """
🕐 Настройка регулярных уведомлений

Используйте команду в формате:
/regular <начальный_час> <конечный_час> <интервал_часов>

Примеры:
/regular 10 22 2    - каждые 2 часа с 10:00 до 22:00
/regular 8 20 4     - каждые 4 часа с 8:00 до 20:00
/regular 9 18 3     - каждые 3 часа с 9:00 до 18:00

Часы указываются в формате 24 часа (0-23)
"""
        bot.send_message(user_id, help_text)
        return
    
    try:
        start_hour = int(command_parts[1])
        end_hour = int(command_parts[2])
        interval_hours = int(command_parts[3])
        
        # Проверяем корректность параметров
        if not (0 <= start_hour <= 23 and 0 <= end_hour <= 23):
            bot.send_message(user_id, "❌ Часы должны быть от 0 до 23")
            return
            
        if start_hour >= end_hour:
            bot.send_message(user_id, "❌ Начальный час должен быть меньше конечного")
            return
            
        if interval_hours < 1 or interval_hours > 12:
            bot.send_message(user_id, "❌ Интервал должен быть от 1 до 12 часов")
            return
        
        # Добавляем регулярные уведомления
        if notification_scheduler.add_regular_notification(user_id, start_hour, end_hour, interval_hours):
            times_list = []
            current_hour = start_hour
            while current_hour <= end_hour:
                times_list.append(f"{current_hour:02d}:00")
                current_hour += interval_hours
            
            times_text = ", ".join(times_list)
            bot.send_message(
                user_id, 
                f"✅ Регулярные уведомления настроены!\n\n"
                f"Время отправки: {times_text}\n"
                f"Интервал: каждые {interval_hours} часа(ов)\n"
                f"Диапазон: {start_hour:02d}:00 - {end_hour:02d}:00"
            )
        else:
            bot.send_message(user_id, "❌ Ошибка при настройке регулярных уведомлений")
            
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат параметров. Используйте числа от 0 до 23")
    except Exception as e:
        logger.error(f"Ошибка команды /regular: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при настройке уведомлений")


def send_weather_info(user_id, city, weather_type, lat=None, lon=None):
    """Отправляет информацию о погоде пользователю."""
    try:
        # Отправляем сообщение о загрузке
        loading_msg = bot.send_message(user_id, f"🌤️ Получаем данные о погоде для {city}...")
        
        # Если координаты не переданы, пытаемся получить их из настроек пользователя
        if lat is None or lon is None:
            user_coordinates = user_manager.get_user_coordinates(user_id)
            if user_coordinates:
                lat, lon = user_coordinates
                logger.info(f"Используем сохраненные координаты пользователя {user_id}: {lat}, {lon}")
        
        if weather_type == "current":
            if lat and lon:
                weather_data = get_weather_by_coordinates(lat, lon)
            else:
                # Если нет координат, то получаем координаты из названия города. Берем первый город из списка.
                cities_data = get_cities_list(city)
                if "error" in cities_data:
                    message = f"❌ Ошибка: {cities_data['error']}"
                    return
                weather_data = get_weather_by_coordinates(cities_data["cities"][0]["lat"], cities_data["cities"][0]["lon"])
            if "error" in weather_data:
                message = f"❌ Ошибка: {weather_data['error']}"
            else:
                message = f"🌤️ Погода в {city}\n\n{format_weather_data(weather_data)}"
        
        elif weather_type == "forecast":
            if lat and lon:
                weather_data = get_daily_weather(lat, lon)
            else:
                weather_data = get_daily_weather_by_city(city)
            if "error" in weather_data:
                message = f"❌ Ошибка: {weather_data['error']}"
            else:
                message = f"📅 Прогноз погоды для {city}\n\n{format_daily_weather(weather_data)}"
        
        elif weather_type == "hourly":
            if lat and lon:
                weather_data = get_hourly_weather(lat, lon)
            else:
                weather_data = get_hourly_weather_by_city(city)
            if "error" in weather_data:
                message = f"❌ Ошибка: {weather_data['error']}"
            else:
                message = f"⏰ Почасовой прогноз для {city}\n\n{format_hourly_weather(weather_data)}"
        
        elif weather_type == "air":
            if lat and lon:
                weather_data = get_air_pollution(lat, lon)
            else:
                weather_data = get_air_pollution_by_city(city)
            if "error" in weather_data:
                message = f"❌ Ошибка: {weather_data['error']}"
            else:
                message = f"🌬️ Качество воздуха в {city}\n\n{analyze_air_pollution(weather_data)}"
        
        # Удаляем сообщение о загрузке и отправляем результат
        bot.delete_message(user_id, loading_msg.message_id)
        bot.send_message(user_id, message, reply_markup=create_main_keyboard(), parse_mode='HTML')
        
        # Обновляем активность пользователя
        user_manager.update_last_activity(user_id)
        
    except Exception as e:
        logger.error(f"Ошибка отправки погодной информации: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при получении данных о погоде")


def handle_city_search(user_id, city_query, weather_type):
    """Обрабатывает поиск города и показывает список для выбора."""
    try:
        # Получаем список городов
        cities_data = get_cities_list(city_query)
        
        if "error" in cities_data:
            bot.send_message(user_id, f"❌ {cities_data['error']}")
            return
        
        cities = cities_data["cities"]
        
        if len(cities) == 1:
            # Если найден только один город
            if weather_type == "set_city":
                # Устанавливаем город по умолчанию
                city_name = cities[0]['display_name']
                if user_manager.update_user_city(user_id, city_name):
                    bot.send_message(user_id, f"✅ Город по умолчанию установлен: {city_name}", reply_markup=create_settings_keyboard())
                    logger.info(f"Пользователь {user_id} установил город: {city_name}")
                else:
                    bot.send_message(user_id, "❌ Ошибка при установке города", reply_markup=create_settings_keyboard())
            else:
                # Показываем погоду используя координаты
                city_info = cities[0]
                send_weather_info(user_id, city_info['display_name'], weather_type, city_info['lat'], city_info['lon'])
        else:
            # Если найдено несколько городов, показываем список для выбора
            city_selection_data[user_id] = {
                "city_query": city_query,
                "weather_type": weather_type,
                "cities": cities
            }
            
            if weather_type == "set_city":
                message = f"🔎 Найдено {len(cities)} городов с названием '{city_query}':\n\nВыберите город для установки по умолчанию:"
            else:
                message = f"🔎 Найдено {len(cities)} городов с названием '{city_query}':\n\nВыберите нужный город:"
            
            bot.send_message(
                user_id, 
                message, 
                reply_markup=create_city_selection_keyboard(cities_data)
            )
    
    except Exception as e:
        logger.error(f"Ошибка поиска города: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при поиске города")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Обработчик всех callback запросов."""
    user_id = call.from_user.id
    ensure_user_exists(user_id)
    
    try:
        # Обработка выбора города из списка
        if call.data.startswith("select_city_"):
            city_index = int(call.data.split("_")[2])
            
            if user_id in city_selection_data:
                selection_data = city_selection_data[user_id]
                cities = selection_data["cities"]
                weather_type = selection_data["weather_type"]
                
                if 0 <= city_index < len(cities):
                    selected_city = cities[city_index]
                    
                    if weather_type == "set_city":
                        # Устанавливаем город по умолчанию с координатами
                        city_name = selected_city['display_name']
                        latitude = selected_city['lat']
                        longitude = selected_city['lon']
                        
                        if user_manager.update_user_city(user_id, city_name, latitude, longitude):
                            success_msg = f"✅ Город по умолчанию установлен!\n\n"
                            success_msg += f"🏙️ Город: {city_name}\n"
                            success_msg += f"📍 Координаты: {latitude:.4f}, {longitude:.4f}\n\n"
                            success_msg += f"💡 Теперь вы можете получать точную погоду для этого города"
                            
                            bot.edit_message_text(
                                success_msg,
                                user_id,
                                call.message.message_id,
                                reply_markup=create_settings_keyboard()
                            )
                            logger.info(f"Пользователь {user_id} установил город: {city_name} ({latitude}, {longitude})")
                        else:
                            bot.edit_message_text(
                                "❌ Ошибка при установке города",
                                user_id,
                                call.message.message_id,
                                reply_markup=create_settings_keyboard()
                            )
                    else:
                        # Показываем погоду для выбранного города используя координаты
                        city_info = selected_city
                        send_weather_info(user_id, city_info['display_name'], weather_type, city_info['lat'], city_info['lon'])
                        bot.delete_message(user_id, call.message.message_id)
                    
                    # Удаляем данные выбора
                    del city_selection_data[user_id]
                else:
                    bot.answer_callback_query(call.id, "❌ Неверный выбор города")
            else:
                bot.answer_callback_query(call.id, "❌ Данные выбора города не найдены")
        
        elif call.data == "cancel_city_selection":
            if user_id in city_selection_data:
                del city_selection_data[user_id]
            bot.edit_message_text(
                "❌ Выбор города отменен",
                user_id,
                call.message.message_id
            )
        
        elif call.data == "weather_current":
            city = user_manager.get_user_city(user_id)
            coordinates = user_manager.get_user_coordinates(user_id)
            
            if city:
                if coordinates:
                    # Используем сохраненные координаты для точной погоды
                    lat, lon = coordinates
                    send_weather_info(user_id, city, "current", lat, lon)
                else:
                    # Если нет координат, используем поиск по названию
                    handle_city_search(user_id, city, "current")
            else:
                bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
        
        elif call.data == "weather_forecast":
            city = user_manager.get_user_city(user_id)
            coordinates = user_manager.get_user_coordinates(user_id)
            
            if city:
                if coordinates:
                    # Используем сохраненные координаты для точного прогноза
                    lat, lon = coordinates
                    send_weather_info(user_id, city, "forecast", lat, lon)
                else:
                    # Если нет координат, используем поиск по названию
                    handle_city_search(user_id, city, "forecast")
            else:
                bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
        
        elif call.data == "weather_daily":
            city = user_manager.get_user_city(user_id)
            coordinates = user_manager.get_user_coordinates(user_id)
            
            if city:
                if coordinates:
                    # Используем сохраненные координаты для точного прогноза
                    lat, lon = coordinates
                    send_weather_info(user_id, city, "forecast", lat, lon)
                else:
                    # Если нет координат, используем поиск по названию
                    handle_city_search(user_id, city, "forecast")
            else:
                bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
        
        elif call.data == "weather_hourly":
            city = user_manager.get_user_city(user_id)
            coordinates = user_manager.get_user_coordinates(user_id)
            
            if city:
                if coordinates:
                    # Используем сохраненные координаты для точного прогноза
                    lat, lon = coordinates
                    send_weather_info(user_id, city, "hourly", lat, lon)
                else:
                    # Если нет координат, используем поиск по названию
                    handle_city_search(user_id, city, "hourly")
            else:
                bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
        
        elif call.data == "weather_air":
            city = user_manager.get_user_city(user_id)
            coordinates = user_manager.get_user_coordinates(user_id)
            
            if city:
                if coordinates:
                    # Используем сохраненные координаты для точного анализа воздуха
                    lat, lon = coordinates
                    send_weather_info(user_id, city, "air", lat, lon)
                else:
                    # Если нет координат, используем поиск по названию
                    handle_city_search(user_id, city, "air")
            else:
                bot.send_message(user_id, "❌ Город по умолчанию не установлен. Используйте /setcity [город]")
        
        elif call.data == "settings":
            bot.edit_message_text(
                "⚙️ Настройки",
                user_id,
                call.message.message_id,
                reply_markup=create_settings_keyboard()
            )
        
        elif call.data == "change_city":
            text = """
🏙️ Изменить город по умолчанию

Выберите способ установки города:

✏️ Ввести вручную - введите название города
📍 Получить автоматически - используйте геолокацию

💡 Город по умолчанию используется для уведомлений и быстрого доступа к погоде
"""
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=create_city_setting_keyboard()
            )
        
        elif call.data == "city_manual":
            bot.send_message(
                user_id,
                "✏️ Введите название города для установки по умолчанию:\n\n"
                "💡 Примеры: Москва, London, New York, Санкт-Петербург\n"
                "🌍 Поддерживаются города на разных языках\n\n"
                "💡 Для отмены введите команду /start"
            )
            bot.register_next_step_handler(call.message, process_city_input_for_settings)
        
        elif call.data == "city_auto":
            # Создаем клавиатуру с кнопкой геолокации
            location_keyboard = types.ReplyKeyboardMarkup(
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            location_btn = types.KeyboardButton("📍 Отправить мою геолокацию", request_location=True)
            cancel_btn = types.KeyboardButton("❌ Отмена")
            location_keyboard.add(location_btn, cancel_btn)
            
            bot.send_message(
                user_id,
                "📍 Получить город автоматически\n\n"
                "Нажмите кнопку ниже, чтобы отправить вашу геолокацию:\n"
                "• Бот определит ваш город по координатам\n"
                "• Установит его как город по умолчанию\n"
                "• Данные геолокации не сохраняются\n\n"
                "🔒 Ваша геолокация используется только для определения города",
                reply_markup=location_keyboard
            )
            bot.register_next_step_handler(call.message, process_location_input)
        
        elif call.data == "notification_settings":
            user_data = user_manager.get_user_data(user_id)
            notifications_enabled = user_data.get("notifications_enabled", False)
            notification_times = user_data.get("notification_times", ["08:00", "18:00"])
            
            status_text = "включены" if notifications_enabled else "выключены"
            times_text = ", ".join(notification_times)
            
            text = f"""
🔔 Настройки уведомлений:

Статус: {status_text}
Время отправки: {times_text}

Используйте кнопки ниже для изменения настроек:
"""
            
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=create_notification_keyboard(user_id)
            )
        
        elif call.data == "forecast_settings":
            # Импортируем COUNT_3_HOURS_FORECAST из weather модуля
            from weather import COUNT_3_HOURS_FORECAST
            
            text = f"""
📊 Настройки прогноза:

Текущее количество 3-часовых интервалов: {COUNT_3_HOURS_FORECAST}
Общее время прогноза: {COUNT_3_HOURS_FORECAST * 3} часов

Выберите количество интервалов:
• 8 интервалов = 24 часа (1 день)
• 16 интервалов = 48 часов (2 дня)  
• 24 интервала = 72 часа (3 дня)
• 40 интервалов = 120 часов (5 дней)
"""
            
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=create_forecast_settings_keyboard()
            )
        
        elif call.data.startswith("forecast_count_"):
            # Обработка изменения количества прогнозов
            count_str = call.data.split("_")[2]
            try:
                new_count = int(count_str)
                # Обновляем глобальную переменную в weather модуле
                import weather
                weather.COUNT_3_HOURS_FORECAST = new_count
                
                bot.edit_message_text(
                    f"✅ Количество прогнозов изменено на {new_count} интервалов ({new_count * 3} часов)",
                    user_id,
                    call.message.message_id,
                    reply_markup=create_settings_keyboard()
                )
                logger.info(f"Пользователь {user_id} изменил количество прогнозов на {new_count}")
            except ValueError:
                bot.answer_callback_query(call.id, "❌ Ошибка при изменении настроек")
        
        elif call.data.startswith("forecast_count_"):
            # Обработка изменения количества прогнозов
            count_str = call.data.split("_")[2]
            try:
                new_count = int(count_str)
                # Обновляем глобальную переменную в weather модуле
                import weather
                weather.COUNT_3_HOURS_FORECAST = new_count
                
                bot.edit_message_text(
                    f"✅ Количество прогнозов изменено на {new_count} интервалов ({new_count * 3} часов)",
                    user_id,
                    call.message.message_id,
                    reply_markup=create_settings_keyboard()
                )
                logger.info(f"Пользователь {user_id} изменил количество прогнозов на {new_count}")
            except ValueError:
                bot.answer_callback_query(call.id, "❌ Ошибка при изменении настроек")
        
        elif call.data == "frequency_settings":
            text = """
⏰ Настройка частоты уведомлений

Выберите тип частоты уведомлений:

🕐 Заданное время - уведомления в конкретное время (например: 08:00, 18:00)
⏱️ Каждые Х часов - регулярные уведомления через заданный интервал

Текущие настройки можно изменить в разделе "Настройки уведомлений"
"""
            
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=create_frequency_settings_keyboard()
            )
        
        elif call.data == "frequency_fixed_time":
            instruction_msg = """
🕐 Настройка уведомлений по заданному времени

📝 Введите время в формате HH:MM

📋 Примеры ввода:
• 08:00 - одно уведомление в 8:00
• 08:00,18:00 - два уведомления в 8:00 и 18:00
• 08:00 18:00 - то же самое (через пробел)
• 09:30,12:15,18:45 - три уведомления

⏰ Правила:
• Часы: 0-23
• Минуты: 0-59
• Можно использовать запятые или пробелы
• Время автоматически сортируется

💡 Для отмены введите команду /start
"""
            bot.send_message(user_id, instruction_msg)
            bot.register_next_step_handler(call.message, process_fixed_time_input)
        
        elif call.data == "frequency_interval":
            bot.send_message(
                user_id,
                "⏱️ Настройка регулярных уведомлений\n\n"
                "Используйте команду /regular для настройки интервалов\n"
                "Формат: /regular <начальный_час> <конечный_час> <интервал_часов>\n\n"
                "Пример: /regular 10 22 2 (каждые 2 часа с 10:00 до 22:00)"
            )
        
        elif call.data == "toggle_notifications":
            user_data = user_manager.get_user_data(user_id)
            current_status = user_data.get("notifications_enabled", False)
            new_status = not current_status
            
            if user_manager.update_notification_settings(user_id, new_status):
                status_text = "включены" if new_status else "выключены"
                bot.answer_callback_query(call.id, f"Уведомления {status_text}")
                
                # Перепланируем уведомления
                notification_scheduler.reschedule_user_notifications(user_id)
                
                # Обновляем клавиатуру
                bot.edit_message_reply_markup(
                    user_id,
                    call.message.message_id,
                    reply_markup=create_notification_keyboard(user_id)
                )
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка при изменении настроек")
        
        elif call.data == "change_notification_times":
            bot.send_message(user_id, "⏰ Введите время уведомлений в формате HH:MM через запятую (например: 08:00,18:00):")
            bot.register_next_step_handler(call.message, process_notification_times_input)
        
        elif call.data == "back_to_main":
            bot.edit_message_text(
                "🌤️ Главное меню",
                user_id,
                call.message.message_id,
                reply_markup=create_main_keyboard()
            )
        
        elif call.data == "help":
            help_text = """
🤖 Weather Bot - Помощник по погоде

📋 Доступные команды:
/start - Главное меню
/weather [город] - Текущая погода
/forecast [город] - Прогноз на 5 дней
/hourly [город] - Почасовой прогноз
/air [город] - Качество воздуха
/setcity [город] - Установить город по умолчанию
/notifications - Настройки уведомлений
/regular - Регулярные уведомления
/help - Справка

💡 Просто введите название города для получения текущей погоды!

⚙️ Настройки:
• Изменить город - установить город по умолчанию:
  ✏️ Ввести вручную - введите название города
  📍 Получить автоматически - используйте геолокацию
• Настройки уведомлений - включить/выключить уведомления
• Настроить частоту - выбрать тип уведомлений:
  🕐 Заданное время (08:00, 18:00)
  ⏱️ Каждые Х часов (/regular 10 22 2)
• Настройки прогноза - количество интервалов (8-40)

🕐 Регулярные уведомления:
/regular 10 22 2 - каждые 2 часа с 10:00 до 22:00

🌐 Данные предоставляются OpenWeatherMap
"""
            bot.edit_message_text(
                help_text,
                user_id,
                call.message.message_id,
                reply_markup=create_main_keyboard()
            )
        
        elif call.data == "back_to_settings":
            bot.edit_message_text(
                "⚙️ Настройки",
                user_id,
                call.message.message_id,
                reply_markup=create_settings_keyboard()
            )
        
        elif call.data == "help":
            help_text = """
❓ Справка по командам:

/start - Главное меню
/weather [город] - Текущая погода
/forecast [город] - Прогноз на 5 дней  
/hourly [город] - Почасовой прогноз
/air [город] - Качество воздуха
/setcity [город] - Установить город по умолчанию
/notifications - Настройки уведомлений
/help - Эта справка

💡 Совет: Если не указать город, будет использован ваш город по умолчанию.

🔔 Уведомления: Вы можете настроить автоматические уведомления о погоде в удобное время.
"""
            bot.send_message(user_id, help_text)
        
        # Подтверждаем получение callback
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Ошибка обработки callback: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def process_location_input(message):
    """Обрабатывает геолокацию пользователя для определения города."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    try:
        # Проверяем, что пользователь отправил геолокацию
        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude
            
            # Убираем клавиатуру геолокации
            remove_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(user_id, "📍 Получаем информацию о вашем городе...", reply_markup=remove_keyboard)
            
            # Получаем город по координатам
            city_data = get_city_by_coordinates(latitude, longitude)
            
            if "error" in city_data:
                bot.send_message(
                    user_id,
                    f"❌ Не удалось определить город: {city_data['error']}\n\n"
                    "💡 Попробуйте использовать ручной ввод города",
                    reply_markup=create_settings_keyboard()
                )
                return
            
            # Извлекаем название города
            city_name = city_data.get("name", "Неизвестно")
            country = city_data.get("country", "")
            state = city_data.get("state", "")
            
            # Формируем полное название
            full_city_name = city_name
            if state:
                full_city_name += f", {state}"
            if country:
                full_city_name += f", {country}"
            
            # Обновляем город пользователя с координатами
            if user_manager.update_user_city(user_id, full_city_name, latitude, longitude):
                success_msg = f"✅ Город по умолчанию установлен!\n\n"
                success_msg += f"🏙️ Город: {full_city_name}\n"
                success_msg += f"📍 Координаты: {latitude:.4f}, {longitude:.4f}\n\n"
                success_msg += f"💡 Теперь вы можете получать точную погоду для этого города"
                
                bot.send_message(
                    user_id,
                    success_msg,
                    reply_markup=create_settings_keyboard()
                )
                
                logger.info(f"Пользователь {user_id} установил город по геолокации: {full_city_name} ({latitude}, {longitude})")
                
            else:
                bot.send_message(
                    user_id,
                    "❌ Ошибка при сохранении города\n\n"
                    "Попробуйте еще раз или обратитесь к администратору",
                    reply_markup=create_settings_keyboard()
                )
                
        elif message.text and message.text.strip() == "❌ Отмена":
            # Убираем клавиатуру и возвращаемся в настройки
            remove_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(
                user_id,
                "❌ Отмена установки города",
                reply_markup=remove_keyboard
            )
            bot.send_message(
                user_id,
                "⚙️ Настройки",
                reply_markup=create_settings_keyboard()
            )
            
        else:
            # Неожиданный ввод
            remove_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(
                user_id,
                "❌ Пожалуйста, отправьте геолокацию или нажмите 'Отмена'",
                reply_markup=remove_keyboard
            )
            bot.send_message(
                user_id,
                "⚙️ Настройки",
                reply_markup=create_settings_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка обработки геолокации: {e}")
        remove_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(
            user_id,
            "❌ Произошла ошибка при обработке геолокации\n\n"
            "Попробуйте еще раз или используйте ручной ввод города",
            reply_markup=remove_keyboard
        )
        bot.send_message(
            user_id,
            "⚙️ Настройки",
            reply_markup=create_settings_keyboard()
        )


def process_city_input_for_settings(message):
    """Обрабатывает ввод города пользователем в настройках."""
    user_id = message.from_user.id
    city = message.text.strip()
    
    # Используем поиск города для выбора
    city_selection_data[user_id] = {
        "city_query": city,
        "weather_type": "set_city",  # Специальный тип для установки города
        "cities": []
    }
    
    handle_city_search(user_id, city, "set_city")


def process_city_input(message):
    """Обрабатывает ввод города пользователем."""
    user_id = message.from_user.id
    city = message.text.strip()
    
    if user_manager.update_user_city(user_id, city):
        bot.send_message(user_id, f"✅ Город по умолчанию установлен: {city}")
        logger.info(f"Пользователь {user_id} установил город: {city}")
    else:
        bot.send_message(user_id, "❌ Ошибка при установке города")


def process_fixed_time_input(message):
    """Обрабатывает ввод точного времени для фиксированных уведомлений."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    try:
        time_input = message.text.strip()
        
        # Если пользователь ввел команду, обрабатываем её
        if time_input.startswith('/'):
            return
        
        # Парсим время (формат: HH:MM,HH:MM или HH:MM HH:MM)
        times = []
        invalid_times = []
        
        # Разделяем по запятым и пробелам
        time_parts = time_input.replace(',', ' ').split()
        
        for time_str in time_parts:
            time_str = time_str.strip()
            
            # Проверяем формат времени
            if ':' in time_str:
                try:
                    hour_str, minute_str = time_str.split(':')
                    hour = int(hour_str)
                    minute = int(minute_str)
                    
                    # Проверяем корректность времени
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        formatted_time = f"{hour:02d}:{minute:02d}"
                        if formatted_time not in times:  # Избегаем дублирования
                            times.append(formatted_time)
                    else:
                        invalid_times.append(time_str)
                        
                except ValueError:
                    invalid_times.append(time_str)
            else:
                invalid_times.append(time_str)
        
        # Проверяем результаты
        if invalid_times:
            error_msg = f"❌ Неверный формат времени: {', '.join(invalid_times)}\n\n"
            error_msg += "✅ Правильный формат: HH:MM\n"
            error_msg += "📝 Примеры: 08:00, 18:30, 12:15\n"
            error_msg += "⏰ Часы: 0-23, минуты: 0-59"
            bot.send_message(user_id, error_msg)
            return
        
        if not times:
            help_msg = """
❌ Не введено ни одного времени

📝 Правильный формат: HH:MM
📋 Примеры ввода:
• 08:00
• 08:00,18:00
• 08:00 18:00
• 09:30,12:15,18:45

⏰ Часы: 0-23, минуты: 0-59
"""
            bot.send_message(user_id, help_msg)
            return
        
        # Сортируем времена для удобства
        times.sort()
        
        # Обновляем настройки пользователя
        if user_manager.update_notification_settings(user_id, True, times):
            times_text = ", ".join(times)
            
            # Формируем информативное сообщение
            success_msg = f"✅ Уведомления настроены!\n\n"
            success_msg += f"🕐 Время отправки: {times_text}\n"
            success_msg += f"📊 Количество уведомлений: {len(times)}\n"
            success_msg += f"🏙️ Город: {user_manager.get_user_city(user_id) or 'Не установлен'}\n\n"
            success_msg += f"💡 Для изменения времени используйте команду /notifications"
            
            bot.send_message(
                user_id,
                success_msg,
                reply_markup=create_settings_keyboard()
            )
            
            logger.info(f"Пользователь {user_id} установил время уведомлений: {times_text}")
            
            # Перепланируем уведомления
            notification_scheduler.schedule_notifications()
            
        else:
            bot.send_message(
                user_id, 
                "❌ Ошибка при сохранении настроек\n\n"
                "Попробуйте еще раз или обратитесь к администратору"
            )
            
    except ValueError:
        error_msg = """
❌ Неверный формат времени

📝 Правильный формат: HH:MM
📋 Примеры ввода:
• 08:00
• 08:00,18:00  
• 08:00 18:00
• 09:30,12:15,18:45

⏰ Часы: 0-23, минуты: 0-59
"""
        bot.send_message(user_id, error_msg)
        
    except Exception as e:
        logger.error(f"Ошибка обработки времени: {e}")
        bot.send_message(
            user_id, 
            "❌ Произошла ошибка при обработке времени\n\n"
            "Попробуйте еще раз или обратитесь к администратору"
        )


def process_notification_times_input(message):
    """Обрабатывает ввод времени уведомлений пользователем."""
    user_id = message.from_user.id
    times_text = message.text.strip()
    
    try:
        # Парсим времена
        times = [time.strip() for time in times_text.split(',')]
        
        # Проверяем формат времени
        for time_str in times:
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                bot.send_message(user_id, f"❌ Неверный формат времени: {time_str}. Используйте HH:MM")
                return
        
        # Обновляем настройки
        if user_manager.update_notification_settings(user_id, True, times):
            times_display = ", ".join(times)
            bot.send_message(user_id, f"✅ Время уведомлений установлено: {times_display}")
            
            # Перепланируем уведомления
            notification_scheduler.reschedule_user_notifications(user_id)
            
            logger.info(f"Пользователь {user_id} установил время уведомлений: {times}")
        else:
            bot.send_message(user_id, "❌ Ошибка при установке времени уведомлений")
    
    except Exception as e:
        logger.error(f"Ошибка обработки времени уведомлений: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при обработке времени")

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown."""
    logger.info("Получен сигнал завершения. Останавливаем бота...")
    notification_scheduler.stop_scheduler()
    sys.exit(0)


@bot.message_handler(func=lambda message: True)
def handle_text_message(message):
    """Обработчик всех текстовых сообщений - показывает погоду для введенного города."""
    user_id = message.from_user.id
    ensure_user_exists(user_id)
    
    city_query = message.text.strip()
    
    # Игнорируем команды (они обрабатываются отдельными обработчиками)
    if city_query.startswith('/'):
        return
    
    # Игнорируем слишком короткие запросы
    if len(city_query) < 2:
        bot.send_message(user_id, "❌ Название города слишком короткое. Попробуйте еще раз.")
        return
    
    try:
        # Получаем список городов
        cities_data = get_cities_list(city_query)
        
        if "error" in cities_data:
            bot.send_message(user_id, f"❌ {cities_data['error']}")
            return
        
        cities = cities_data["cities"]
        
        if len(cities) == 0:
            bot.send_message(user_id, f"❌ Город '{city_query}' не найден. Попробуйте другое название.")
            return
        
        # Автоматически выбираем первый город из списка
        selected_city = cities[0]
        city_name = selected_city['display_name']
        
        # Показываем текущую погоду для выбранного города
        send_weather_info(user_id, city_name, "current", selected_city['lat'], selected_city['lon'])
        
        logger.info(f"Пользователь {user_id} запросил погоду для города: {city_name}")
        
    except Exception as e:
        logger.error(f"Ошибка обработки текстового сообщения: {e}")
        bot.send_message(user_id, "❌ Произошла ошибка при поиске города")


def main():
    """Основная функция запуска бота."""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Запуск Weather Bot...")
    
    try:
        # Запускаем планировщик уведомлений
        notification_scheduler.start_scheduler()
        
        # Запускаем бота
        logger.info("Бот запущен и готов к работе!")
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Остановка бота...")
        notification_scheduler.stop_scheduler()


if __name__ == "__main__":
    main()