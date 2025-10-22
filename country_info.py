"""
Country Information Module
Handles country data retrieval and display formatting.
"""

import re
from typing import Dict, Any, Tuple
from colorama import Fore, Style
from api_client import make_get_request


def get_country_data(country_name: str) -> Tuple[bool, Dict[str, Any], str]:
    """
    Retrieve country data from RestCountries API.
    
    Args:
        country_name: Name of the country to search for
        
    Returns:
        Tuple of (success, data, error_message)
    """
    if not country_name.strip():
        return False, {}, "Название страны не может быть пустым!"
    
    url = f"https://restcountries.com/v3.1/name/{country_name}"
    status_code, data, error = make_get_request(url)
    
    if error:
        return False, {}, error
    
    if not data or not isinstance(data, list) or len(data) == 0:
        return False, {}, "Страна не найдена!"
    
    return True, data[0], ""  # Take first result


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


def get_weather_data(capital_name: str, latitude: float, longitude: float) -> Tuple[bool, Dict[str, Any], str]:
    """
    Retrieve weather data for a capital city.
    
    Args:
        capital_name: Name of the capital city
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        Tuple of (success, weather_data, error_message)
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'current': 'temperature_2m,wind_speed_10m,relative_humidity_2m,weather_code'
    }
    
    status_code, data, error = make_get_request(url, params)
    
    if error:
        return False, {}, f"Ошибка получения данных о погоде: {error}"
    
    if not data or 'current' not in data:
        return False, {}, "Не удалось получить данные о погоде!"
    
    return True, data, ""


def format_country_basic_info(country: Dict[str, Any]) -> str:
    """
    Format basic country information for display.
    
    Args:
        country: Country data dictionary
        
    Returns:
        Formatted string with basic country information
    """
    lines = []
    
    # Basic information
    lines.append(f"{Fore.MAGENTA}Название (официальное):{Style.RESET_ALL} {Fore.WHITE}{country.get('name', {}).get('official', 'Неизвестно')}{Style.RESET_ALL}")
    
    lines.append(f"{Fore.MAGENTA}Столица:{Style.RESET_ALL} {Fore.WHITE}{', '.join(country.get('capital', [])) if country.get('capital') else 'Неизвестно'}{Style.RESET_ALL}")
    
    population = country.get('population', 0)
    lines.append(f"{Fore.MAGENTA}Население:{Style.RESET_ALL} {Fore.WHITE}{population:, if population else 'Неизвестно'}{Style.RESET_ALL}")
    
    lines.append(f"{Fore.MAGENTA}Регион:{Style.RESET_ALL} {Fore.WHITE}{country.get('region', 'Неизвестно')}{Style.RESET_ALL}")
    lines.append(f"{Fore.MAGENTA}Субрегион:{Style.RESET_ALL} {Fore.WHITE}{country.get('subregion', 'Неизвестно')}{Style.RESET_ALL}")
    
    # Languages
    languages = country.get('languages', {})
    if languages:
        lang_names = list(languages.values())
        lines.append(f"{Fore.MAGENTA}Языки:{Style.RESET_ALL} {Fore.WHITE}{', '.join(lang_names)}{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.MAGENTA}Языки:{Style.RESET_ALL} {Fore.WHITE}Неизвестно{Style.RESET_ALL}")
    
    # Currency
    currencies = country.get('currencies', {})
    if currencies:
        currency_info = []
        for code, info in currencies.items():
            name = info.get('name', code)
            symbol = info.get('symbol', '')
            currency_info.append(f"{name} ({symbol})")
        lines.append(f"{Fore.MAGENTA}Валюта:{Style.RESET_ALL} {Fore.WHITE}{', '.join(currency_info)}{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.MAGENTA}Валюта:{Style.RESET_ALL} {Fore.WHITE}Неизвестно{Style.RESET_ALL}")
    
    # Flag
    flags = country.get('flags', {})
    flag_png = flags.get('png', '')
    if flag_png:
        lines.append(f"{Fore.MAGENTA}Флаг (PNG):{Style.RESET_ALL} {Fore.WHITE}{flag_png}{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.MAGENTA}Флаг (PNG):{Style.RESET_ALL} {Fore.WHITE}Неизвестно{Style.RESET_ALL}")
    
    # Borders
    borders = country.get('borders', [])
    if borders:
        lines.append(f"{Fore.MAGENTA}Границы с соседями:{Style.RESET_ALL} {Fore.WHITE}{', '.join(borders)}{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.MAGENTA}Границы с соседями:{Style.RESET_ALL} {Fore.WHITE}Нет данных{Style.RESET_ALL}")
    
    # Timezones
    timezones = country.get('timezones', [])
    if timezones:
        lines.append(f"{Fore.MAGENTA}Часовые пояса:{Style.RESET_ALL} {Fore.WHITE}{', '.join(timezones)}{Style.RESET_ALL}")
    else:
        lines.append(f"{Fore.MAGENTA}Часовые пояса:{Style.RESET_ALL} {Fore.WHITE}Неизвестно{Style.RESET_ALL}")
    
    return '\n'.join(lines)


def format_weather_info(weather_data: Dict[str, Any], capital_name: str) -> str:
    """
    Format weather information for display.
    
    Args:
        weather_data: Weather data dictionary
        capital_name: Name of the capital city
        
    Returns:
        Formatted string with weather information
    """
    lines = []
    
    lines.append(f"{Fore.MAGENTA}Текущая погода в столице:{Style.RESET_ALL} {Fore.WHITE}{capital_name}{Style.RESET_ALL}")
    lines.append("")
    
    current = weather_data['current']
    units = weather_data.get('current_units', {})
    
    # Temperature
    temp = current.get('temperature_2m')
    temp_unit = units.get('temperature_2m', '°C')
    if temp is not None:
        lines.append(f"{Fore.MAGENTA}Температура:{Style.RESET_ALL} {Fore.WHITE}{temp}{temp_unit}{Style.RESET_ALL}")
    
    # Wind speed
    wind_speed = current.get('wind_speed_10m')
    wind_unit = units.get('wind_speed_10m', 'km/h')
    if wind_speed is not None:
        lines.append(f"{Fore.MAGENTA}Скорость ветра:{Style.RESET_ALL} {Fore.WHITE}{wind_speed} {wind_unit}{Style.RESET_ALL}")
    
    # Humidity
    humidity = current.get('relative_humidity_2m')
    if humidity is not None:
        lines.append(f"{Fore.MAGENTA}Влажность:{Style.RESET_ALL} {Fore.WHITE}{humidity}%{Style.RESET_ALL}")
    
    # Weather code description
    weather_code = current.get('weather_code')
    if weather_code is not None:
        weather_desc = get_weather_description(weather_code)
        lines.append(f"{Fore.MAGENTA}Погода:{Style.RESET_ALL} {Fore.WHITE}{weather_desc}{Style.RESET_ALL}")
    
    # Time
    time_str = current.get('time', '')
    if time_str:
        lines.append(f"{Fore.MAGENTA}Время обновления:{Style.RESET_ALL} {Fore.WHITE}{time_str}{Style.RESET_ALL}")
    
    return '\n'.join(lines)


def display_country_with_weather(country_name: str) -> Tuple[bool, str]:
    """
    Display complete country information including weather.
    
    Args:
        country_name: Name of the country to display
        
    Returns:
        Tuple of (success, formatted_output)
    """
    # Get country data
    success, country, error = get_country_data(country_name)
    if not success:
        return False, error
    
    # Format basic country information
    country_info = format_country_basic_info(country)
    
    # Try to get weather information
    capitals = country.get('capital', [])
    capital_coords = country.get('capitalInfo', {}).get('latlng', [])
    
    weather_info = ""
    if capitals and capital_coords and len(capital_coords) == 2:
        weather_success, weather_data, weather_error = get_weather_data(
            capitals[0], capital_coords[0], capital_coords[1]
        )
        
        if weather_success:
            weather_info = "\n" + format_weather_info(weather_data, capitals[0])
        else:
            weather_info = f"\n{Fore.RED}{weather_error}{Style.RESET_ALL}"
    
    # Combine all information
    common_name = country.get('name', {}).get('common', 'Неизвестно')
    header = f"{Fore.GREEN}Информация о стране: {common_name}{Style.RESET_ALL}"
    
    full_output = f"{header}\n{country_info}{weather_info}"
    
    return True, full_output
