"""
CLI API Request Application
Interactive menu-driven application for making GET requests to various APIs.
"""

import json
import re
from colorama import init, Fore, Back, Style
from api_client import make_get_request, parse_query_params
from json_formatter import format_json_for_display
from country_info import display_country_with_weather
from currency import (
    convert_currency, get_favorite_currencies, get_available_currencies,
    format_currency_conversion, is_currency_available, get_currency_rate_from_file,
    update_currency_rates, get_currency_info
)
from weather import get_weather_by_city, get_weather_by_coordinates, format_weather_data

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
    
    success, output = display_country_with_weather(country_name)
    
    if success:
        print_separator()
        print(output)
        print_separator()
    else:
        print_error(output)


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


def display_currency_conversion():
    """Display currency conversion interface."""
    print_header("КОНВЕРТАЦИЯ ВАЛЮТ")
    
    # Get available currencies
    favorite_currencies = get_favorite_currencies()
    all_currencies = get_available_currencies()
    
    print_success("Доступные валюты:")
    print_separator()
    
    # Display favorite currencies
    print_label("Избранные валюты: ")
    print_value(", ".join(favorite_currencies))
    print()
    
    # Display all available currencies (first 20)
    print_label("Все доступные валюты (первые 20): ")
    print_value(", ".join(all_currencies[:20]))
    if len(all_currencies) > 20:
        print(f"{Fore.YELLOW}... и еще {len(all_currencies) - 20} валют{Style.RESET_ALL}")
    print()
    
    # Get source currency
    print_prompt("Введите исходную валюту (например, USD): ")
    from_currency = input().strip().upper()
    
    if not from_currency:
        print_error("Исходная валюта не может быть пустой!")
        return
    
    if not is_currency_available(from_currency):
        print_error(f"Валюта {from_currency} не найдена в базе данных!")
        return
    
    # Get target currency
    print_prompt("Введите целевую валюту (например, EUR): ")
    to_currency = input().strip().upper()
    
    if not to_currency:
        print_error("Целевая валюта не может быть пустой!")
        return
    
    if not is_currency_available(to_currency):
        print_error(f"Валюта {to_currency} не найдена в базе данных!")
        return
    
    if from_currency == to_currency:
        print_error("Исходная и целевая валюты не могут быть одинаковыми!")
        return
    
    # Get amount
    print_prompt("Введите сумму для конвертации: ")
    try:
        amount = float(input().strip())
        if amount <= 0:
            print_error("Сумма должна быть положительным числом!")
            return
    except ValueError:
        print_error("Неверный формат суммы!")
        return
    
    # Perform conversion
    result = convert_currency(amount, from_currency, to_currency)
    
    if result is None:
        print_error(f"Не удалось выполнить конвертацию {from_currency} -> {to_currency}")
        return
    
    # Get exchange rate
    rate = get_currency_rate_from_file(from_currency, to_currency)
    
    print_success("Результат конвертации:")
    print_separator()
    
    print_label("Конвертация: ")
    print_value(format_currency_conversion(amount, from_currency, to_currency, result))
    
    if rate:
        print_label("Курс обмена: ")
        print_value(f"1 {from_currency} = {rate:.6f} {to_currency}")
    
    print_separator()


def display_currency_update():
    """Display currency rates update interface."""
    print_header("ОБНОВЛЕНИЕ КУРСОВ ВАЛЮТ")
    
    print_success("Обновление курсов валют из API...")
    print_separator()
    
    print_label("Избранные валюты для обновления: ")
    favorite_currencies = get_favorite_currencies()
    print_value(", ".join(favorite_currencies))
    print()
    
    print_prompt("Нажмите Enter для начала обновления или 'q' для отмены: ")
    confirm = input().strip().lower()
    
    if confirm == 'q':
        print_error("Обновление отменено.")
        return
    
    print_success("Загружаем актуальные курсы валют...")
    print()
    
    try:
        success = update_currency_rates()
        
        if success:
            print_success("✅ Курсы валют успешно обновлены!")
        else:
            print_error("❌ Ошибка при обновлении курсов валют!")
            print_error("Проверьте подключение к интернету и попробуйте снова.")
    
    except Exception as e:
        print_error(f"❌ Произошла ошибка: {e}")
    
    print_separator()


def display_currency_info():
    """Display currency information with dates."""
    print_header("ИНФОРМАЦИЯ О КУРСАХ ВАЛЮТ")
    
    currency_info_list = get_currency_info()
    
    if not currency_info_list:
        print_error("Нет данных о валютах! Сначала обновите курсы валют.")
        return
    
    print_success("Информация о доступных курсах валют:")
    print_separator()
    
    for info in currency_info_list:
        print_label("Валюта: ")
        print_value(info['currency'])
        
        print_label("Базовый код: ")
        print_value(info['base_code'])
        
        print_label("Последнее обновление: ")
        print_value(info['last_update'])
        
        print_label("Следующее обновление: ")
        print_value(info['next_update'])
        
        print_label("Провайдер: ")
        print_value(info['provider'])
        
        print_label("Количество курсов: ")
        print_value(str(info['rates_count']))
        
        print_separator()
    
    print_success(f"Всего валют в базе: {len(currency_info_list)}")
    print_separator()


def display_weather_by_city():
    """Display weather by city name."""
    print_header("ПОГОДА В ГОРОДЕ")
    
    print_prompt("Введите название города: ")
    city = input().strip()
    
    if not city:
        print_error("Название города не может быть пустым!")
        return
    
    print_success(f"Получаем погоду для города: {city}")
    print_separator()
    
    weather_data = get_weather_by_city(city)
    formatted_weather = format_weather_data(weather_data)
    
    print_value(formatted_weather)
    print_separator()


def display_weather_by_coordinates():
    """Display weather by coordinates."""
    print_header("ПОГОДА ПО КООРДИНАТАМ")
    
    print_prompt("Введите широту (latitude): ")
    try:
        lat = float(input().strip())
        if not -90 <= lat <= 90:
            print_error("Широта должна быть от -90 до 90 градусов!")
            return
    except ValueError:
        print_error("Неверный формат широты!")
        return
    
    print_prompt("Введите долготу (longitude): ")
    try:
        lon = float(input().strip())
        if not -180 <= lon <= 180:
            print_error("Долгота должна быть от -180 до 180 градусов!")
            return
    except ValueError:
        print_error("Неверный формат долготы!")
        return
    
    print_success(f"Получаем погоду для координат: {lat:.4f}, {lon:.4f}")
    print_separator()
    
    weather_data = get_weather_by_coordinates(lat, lon)
    formatted_weather = format_weather_data(weather_data)
    
    print_value(formatted_weather)
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
    print(f"{Fore.WHITE}4.{Style.RESET_ALL} {Fore.YELLOW}Конвертация валют{Style.RESET_ALL}")
    print(f"{Fore.WHITE}5.{Style.RESET_ALL} {Fore.GREEN}Обновление курсов валют{Style.RESET_ALL}")
    print(f"{Fore.WHITE}6.{Style.RESET_ALL} {Fore.CYAN}Информация о курсах валют{Style.RESET_ALL}")
    print(f"{Fore.WHITE}7.{Style.RESET_ALL} {Fore.BLUE}Погода в городе{Style.RESET_ALL}")
    print(f"{Fore.WHITE}8.{Style.RESET_ALL} {Fore.BLUE}Погода по координатам{Style.RESET_ALL}")
    print(f"{Fore.WHITE}9.{Style.RESET_ALL} Выход")
    print_separator()


def main():
    """Main application loop."""
    print_success("Добро пожаловать в CLI API Request Application!")
    
    while True:
        show_menu()
        print_prompt("Введите номер действия (1-9): ")
        
        try:
            choice = input().strip()
            
            if choice == '1':
                display_country_info()
            elif choice == '2':
                display_custom_request()
            elif choice == '3':
                display_dog_image()
            elif choice == '4':
                display_currency_conversion()
            elif choice == '5':
                display_currency_update()
            elif choice == '6':
                display_currency_info()
            elif choice == '7':
                display_weather_by_city()
            elif choice == '8':
                display_weather_by_coordinates()
            elif choice == '9':
                print_success("До свидания!")
                break
            else:
                print_error("Неверный выбор! Пожалуйста, введите число от 1 до 9.")
            
            if choice in ['1', '2', '3', '4', '5', '6', '7', '8']:
                print_prompt("\nНажмите Enter для продолжения...")
                input()
                
        except KeyboardInterrupt:
            print_error("\n\nПрограмма прервана пользователем.")
            break
        except Exception as e:
            print_error(f"Произошла ошибка: {e}")


if __name__ == "__main__":
    main()
