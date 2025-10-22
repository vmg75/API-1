"""
CLI API Request Application
Interactive menu-driven application for making GET requests to various APIs.
"""

import json
import re
from colorama import init, Fore, Back, Style
from api_client import make_get_request, parse_query_params
from json_formatter import format_json_for_display

# Initialize colorama for cross-platform colored output
init(autoreset=True)


def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{text.center(60)}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}{Style.RESET_ALL}")


def print_success(text: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")


def print_error(text: str):
    """Print error message in red."""
    print(f"{Fore.RED}{text}{Style.RESET_ALL}")


def print_prompt(text: str):
    """Print input prompt in yellow."""
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}", end="")


def print_label(text: str, end: str = ""):
    """Print data label in magenta."""
    print(f"{Fore.MAGENTA}{text}{Style.RESET_ALL}", end=end)


def print_value(text: str):
    """Print data value in white."""
    print(f"{Fore.WHITE}{text}{Style.RESET_ALL}")


def print_separator():
    """Print a separator line."""
    print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")


def display_country_info():
    """Display information about a country."""
    print_header("ИНФОРМАЦИЯ О СТРАНЕ")
    
    print_prompt("Введите название страны: ")
    country_name = input().strip()
    
    if not country_name:
        print_error("Название страны не может быть пустым!")
        return
    
    url = f"https://restcountries.com/v3.1/name/{country_name}"
    status_code, data, error = make_get_request(url)
    
    if error:
        print_error(error)
        return
    
    if not data or not isinstance(data, list) or len(data) == 0:
        print_error("Страна не найдена!")
        return
    
    country = data[0]  # Take first result
    
    print_success(f"Информация о стране: {country.get('name', {}).get('common', 'Неизвестно')}")
    print_separator()
    
    # Basic information
    print_label("Название (официальное): ")
    print_value(country.get('name', {}).get('official', 'Неизвестно'))
    
    print_label("Столица: ")
    capitals = country.get('capital', [])
    print_value(', '.join(capitals) if capitals else 'Неизвестно')
    
    print_label("Население: ")
    population = country.get('population', 0)
    print_value(f"{population:,}" if population else 'Неизвестно')
    
    print_label("Регион: ")
    print_value(country.get('region', 'Неизвестно'))
    
    print_label("Субрегион: ")
    print_value(country.get('subregion', 'Неизвестно'))
    
    # Languages
    print_label("Языки: ")
    languages = country.get('languages', {})
    if languages:
        lang_names = list(languages.values())
        print_value(', '.join(lang_names))
    else:
        print_value('Неизвестно')
    
    # Currency
    print_label("Валюта: ")
    currencies = country.get('currencies', {})
    if currencies:
        currency_info = []
        for code, info in currencies.items():
            name = info.get('name', code)
            symbol = info.get('symbol', '')
            currency_info.append(f"{name} ({symbol})")
        print_value(', '.join(currency_info))
    else:
        print_value('Неизвестно')
    
    # Flag
    print_label("Флаг (PNG): ")
    flags = country.get('flags', {})
    flag_png = flags.get('png', '')
    if flag_png:
        print_value(flag_png)
    else:
        print_value('Неизвестно')
    
    # Borders
    print_label("Границы с соседями: ")
    borders = country.get('borders', [])
    if borders:
        print_value(', '.join(borders))
    else:
        print_value('Нет данных')
    
    # Timezones
    print_label("Часовые пояса: ")
    timezones = country.get('timezones', [])
    if timezones:
        print_value(', '.join(timezones))
    else:
        print_value('Неизвестно')
    
    # Weather information
    capitals = country.get('capital', [])
    capital_coords = country.get('capitalInfo', {}).get('latlng', [])
    
    if capitals and capital_coords and len(capital_coords) == 2:
        display_weather(capitals[0], capital_coords[0], capital_coords[1])
    
    print_separator()


def display_weather(capital_name: str, latitude: float, longitude: float):
    """Display current weather for the capital city."""
    print_label("Текущая погода в столице: ")
    print_value(f"{capital_name}")
    print()
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'current': 'temperature_2m,wind_speed_10m,relative_humidity_2m,weather_code'
    }
    
    status_code, data, error = make_get_request(url, params)
    
    if error:
        print_error(f"Ошибка получения данных о погоде: {error}")
        return
    
    if not data or 'current' not in data:
        print_error("Не удалось получить данные о погоде!")
        return
    
    current = data['current']
    units = data.get('current_units', {})
    
    # Temperature
    temp = current.get('temperature_2m')
    temp_unit = units.get('temperature_2m', '°C')
    if temp is not None:
        print_label("Температура: ")
        print_value(f"{temp}{temp_unit}")
    
    # Wind speed
    wind_speed = current.get('wind_speed_10m')
    wind_unit = units.get('wind_speed_10m', 'km/h')
    if wind_speed is not None:
        print_label("Скорость ветра: ")
        print_value(f"{wind_speed} {wind_unit}")
    
    # Humidity
    humidity = current.get('relative_humidity_2m')
    if humidity is not None:
        print_label("Влажность: ")
        print_value(f"{humidity}%")
    
    # Weather code description
    weather_code = current.get('weather_code')
    if weather_code is not None:
        weather_desc = get_weather_description(weather_code)
        print_label("Погода: ")
        print_value(weather_desc)
    
    # Time
    time_str = current.get('time', '')
    if time_str:
        print_label("Время обновления: ")
        print_value(time_str)


def get_weather_description(code: int) -> str:
    """Convert weather code to human-readable description."""
    weather_codes = {
        0: "Ясно",
        1: "Преимущественно ясно",
        2: "Переменная облачность",
        3: "Пасмурно",
        45: "Туман",
        48: "Изморозь",
        51: "Легкая морось",
        53: "Умеренная морось",
        55: "Сильная морось",
        56: "Легкая ледяная морось",
        57: "Сильная ледяная морось",
        61: "Легкий дождь",
        63: "Умеренный дождь",
        65: "Сильный дождь",
        66: "Легкий ледяной дождь",
        67: "Сильный ледяной дождь",
        71: "Легкий снег",
        73: "Умеренный снег",
        75: "Сильный снег",
        77: "Снежные зерна",
        80: "Легкие ливни",
        81: "Умеренные ливни",
        82: "Сильные ливни",
        85: "Легкие снежные ливни",
        86: "Сильные снежные ливни",
        95: "Гроза",
        96: "Гроза с градом",
        99: "Сильная гроза с градом"
    }
    return weather_codes.get(code, f"Неизвестно (код: {code})")


def display_custom_request():
    """Make a custom GET request."""
    print_header("ЗАПРОС ПО ССЫЛКЕ")
    
    print_prompt("Введите URL: ")
    url = input().strip()
    
    if not url:
        print_error("URL не может быть пустым!")
        return
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    print_prompt("Введите параметры запроса (key=value,key2=value2) или нажмите Enter для пропуска: ")
    params_string = input().strip()
    
    params = parse_query_params(params_string) if params_string else None
    
    print_success(f"Отправка запроса к: {url}")
    if params:
        print_success(f"Параметры: {params}")
    
    status_code, data, error = make_get_request(url, params)
    
    if error:
        print_error(error)
        return
    
    print_success(f"Статус ответа: {status_code}")
    print_separator()
    
    if data:
        print_label("Выберите формат отображения:", end="\n")
        print(f"{Fore.WHITE}1.{Style.RESET_ALL} Красивый формат (с отступами)")
        print(f"{Fore.WHITE}2.{Style.RESET_ALL} Компактный формат")
        print(f"{Fore.WHITE}3.{Style.RESET_ALL} Табличный формат")
        print(f"{Fore.WHITE}4.{Style.RESET_ALL} Краткая сводка")
        print(f"{Fore.WHITE}5.{Style.RESET_ALL} {Fore.CYAN}Цветной формат{Style.RESET_ALL} (с подсветкой синтаксиса)")
        print(f"{Fore.WHITE}6.{Style.RESET_ALL} {Fore.CYAN}Цветной компактный{Style.RESET_ALL}")
        print(f"{Fore.WHITE}7.{Style.RESET_ALL} {Fore.CYAN}Цветной табличный{Style.RESET_ALL}")
        
        print_prompt("Введите номер формата (1-7): ")
        format_choice = input().strip()
        
        format_styles = {
            '1': 'pretty',
            '2': 'compact', 
            '3': 'table',
            '4': 'summary',
            '5': 'colorful',
            '6': 'colorful_compact',
            '7': 'colorful_table'
        }
        
        style = format_styles.get(format_choice, 'pretty')
        
        print_label("Ответ сервера:")
        print()
        
        try:
            formatted_output = format_json_for_display(data, style)
            print_value(formatted_output)
        except Exception as e:
            print_error(f"Ошибка форматирования: {e}")
            print_value(str(data))
    else:
        print_value("Пустой ответ")
    
    print_separator()


def display_dog_image():
    """Display random dog image."""
    print_header("СЛУЧАЙНАЯ СОБАКА")
    
    url = "https://dog.ceo/api/breeds/image/random"
    status_code, data, error = make_get_request(url)
    
    if error:
        print_error(error)
        return
    
    if not data or data.get('status') != 'success':
        print_error("Не удалось получить изображение собаки!")
        return
    
    image_url = data.get('message', '')
    
    # Try to extract breed from URL
    breed_match = re.search(r'/breeds/([^/]+)/', image_url)
    breed = breed_match.group(1).replace('-', ' ').title() if breed_match else None
    
    print_success("Случайное изображение собаки:")
    print_separator()
    
    if breed:
        print_label("Порода: ")
        print_value(breed)
        print()
    
    print_label("Ссылка на изображение: ")
    print_value(image_url)
    
    print_separator()


def show_menu():
    """Display the main menu."""
    print_header("CLI API REQUEST APPLICATION")
    print(f"{Fore.CYAN}Выберите действие:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}1.{Style.RESET_ALL} Информация о стране")
    print(f"{Fore.WHITE}2.{Style.RESET_ALL} Запрос по ссылке")
    print(f"{Fore.WHITE}3.{Style.RESET_ALL} Собака")
    print(f"{Fore.WHITE}4.{Style.RESET_ALL} Выход")
    print_separator()


def main():
    """Main application loop."""
    print_success("Добро пожаловать в CLI API Request Application!")
    
    while True:
        show_menu()
        print_prompt("Введите номер действия (1-4): ")
        
        try:
            choice = input().strip()
            
            if choice == '1':
                display_country_info()
            elif choice == '2':
                display_custom_request()
            elif choice == '3':
                display_dog_image()
            elif choice == '4':
                print_success("До свидания!")
                break
            else:
                print_error("Неверный выбор! Пожалуйста, введите число от 1 до 4.")
            
            if choice in ['1', '2', '3']:
                print_prompt("\nНажмите Enter для продолжения...")
                input()
                
        except KeyboardInterrupt:
            print_error("\n\nПрограмма прервана пользователем.")
            break
        except Exception as e:
            print_error(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()
