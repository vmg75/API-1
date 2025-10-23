import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional

FAVORITE_CURRENCY = ['USD', 'EUR', 'GBP', 'CNY', 'RUB']
CURRENCY_FILE = 'cache/currency.json'

def get_currency_rate(currency_code: str) -> float:
    """Get the current exchange rate for a currency."""
    url = f"https://open.er-api.com/v6/latest/{currency_code}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None
#    data = {currency: response.json()['rates'][currency] for currency in FAVORITE_CURRENCY if currency in response.json()['rates']}
#    return data
    return response.json()

def save_to_file(rates: dict) -> None:
    # Write rates to file
    try:
        with open(CURRENCY_FILE, 'w', encoding='utf-8') as f:
            json.dump(rates, f, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении валют: {e}")
        return False
#    print(f"Данные о валютах сохранены в файл currency.json")
    return True

def needs_currency_update(currency_code: str) -> Tuple[bool, str]:
    """
    Check if a currency needs updating based on next update time.
    
    Args:
        currency_code: Currency code to check
        
    Returns:
        Tuple of (needs_update, reason)
    """
    currency_data = load_currency_data()
    if not currency_data or currency_code not in currency_data:
        return True, "Нет данных о валюте"
    
    currency_info = currency_data[currency_code]
    next_update_unix = currency_info.get('time_next_update_unix', 0)
    
    if next_update_unix == 0:
        return True, "Нет информации о времени следующего обновления"
    
    current_time = int(time.time())
    
    if current_time >= next_update_unix:
        return True, "Время обновления наступило"
    else:
        next_update_time = datetime.fromtimestamp(next_update_unix)
        return False, f"Обновление не требуется до {next_update_time.strftime('%Y-%m-%d %H:%M:%S')}"


def update_currency_rates() -> bool:
    all_rates = {}
    updated_count = 0
    skipped_count = 0
    
    for currency in FAVORITE_CURRENCY:
        needs_update, reason = needs_currency_update(currency)
        
        if needs_update:
            print(f"Обновляем {currency}: {reason}")
            rates = get_currency_rate(currency)
            all_rates[currency] = rates
            updated_count += 1
        else:
            print(f"Пропускаем {currency}: {reason}")
            # Keep existing data for skipped currencies
            currency_data = load_currency_data()
            if currency_data and currency in currency_data:
                all_rates[currency] = currency_data[currency]
            skipped_count += 1
    
    print(f"Обновлено валют: {updated_count}, пропущено: {skipped_count}")
    return save_to_file(all_rates)


def load_currency_data() -> Optional[Dict[str, Dict[str, float]]]:
    """
    Load currency data from the JSON file.
    
    Returns:
        Dictionary with currency rates or None if file doesn't exist
    """
    try:
        if not os.path.exists(CURRENCY_FILE):
            return None
        
        with open(CURRENCY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке данных о валютах: {e}")
        return None


def convert_currency(amount: float, from_currency: str, to_currency: str) -> Optional[float]:
    """
    Convert currency from one to another using loaded rates.
    
    Args:
        amount: Amount to convert
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        Converted amount or None if conversion failed
    """
    currency_data = load_currency_data()
    if not currency_data:
        return None
    
    # If converting from a favorite currency
    if from_currency in currency_data:
        currency_info = currency_data[from_currency]
        if 'rates' in currency_info and to_currency in currency_info['rates']:
            return amount * currency_info['rates'][to_currency]
    
    # If converting to a favorite currency, we need to find the reverse rate
    for base_currency, currency_info in currency_data.items():
        if 'rates' in currency_info and to_currency == base_currency and from_currency in currency_info['rates']:
            # Reverse conversion: amount / rate
            return amount / currency_info['rates'][from_currency]
    
    return None


def get_available_currencies() -> List[str]:
    """
    Get list of all available currencies from the loaded data.
    
    Returns:
        List of currency codes
    """
    currency_data = load_currency_data()
    if not currency_data:
        return FAVORITE_CURRENCY
    
    # Get all unique currencies from all rate tables
    all_currencies = set()
    for currency_info in currency_data.values():
        if 'rates' in currency_info:
            all_currencies.update(currency_info['rates'].keys())
    
    return sorted(list(all_currencies))


def get_favorite_currencies() -> List[str]:
    """
    Get list of favorite currencies.
    
    Returns:
        List of favorite currency codes
    """
    return FAVORITE_CURRENCY.copy()


def format_currency_conversion(amount: float, from_currency: str, to_currency: str, result: float) -> str:
    """
    Format currency conversion result for display.
    
    Args:
        amount: Original amount
        from_currency: Source currency
        to_currency: Target currency
        result: Converted amount
        
    Returns:
        Formatted string
    """
    return f"{amount:,.2f} {from_currency} = {result:,.2f} {to_currency}"


def is_currency_available(currency: str) -> bool:
    """
    Check if currency is available in the loaded data.
    
    Args:
        currency: Currency code to check
        
    Returns:
        True if currency is available
    """
    currency_data = load_currency_data()
    if not currency_data:
        return False
    
    # Check if currency exists in any rate table
    for currency_info in currency_data.values():
        if 'rates' in currency_info and currency in currency_info['rates']:
            return True
    
    return False


def get_currency_rate_from_file(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Get exchange rate between two currencies from loaded data.
    
    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        
    Returns:
        Exchange rate or None if not found
    """
    currency_data = load_currency_data()
    if not currency_data:
        return None
    
    # Direct rate lookup
    if from_currency in currency_data:
        currency_info = currency_data[from_currency]
        if 'rates' in currency_info and to_currency in currency_info['rates']:
            return currency_info['rates'][to_currency]
    
    # Reverse rate lookup
    for base_currency, currency_info in currency_data.items():
        if 'rates' in currency_info and to_currency == base_currency and from_currency in currency_info['rates']:
            return 1.0 / currency_info['rates'][from_currency]
    
    return None


def get_currency_info() -> List[Dict[str, str]]:
    """
    Get information about available currencies with their update dates.
    
    Returns:
        List of dictionaries with currency information
    """
    currency_data = load_currency_data()
    if not currency_data:
        return []
    
    currency_info_list = []
    for currency_code, currency_info in currency_data.items():
        info = {
            'currency': currency_code,
            'base_code': currency_info.get('base_code', currency_code),
            'last_update': currency_info.get('time_last_update_utc', 'Неизвестно'),
            'next_update': currency_info.get('time_next_update_utc', 'Неизвестно'),
            'provider': currency_info.get('provider', 'Неизвестно'),
            'rates_count': len(currency_info.get('rates', {}))
        }
        currency_info_list.append(info)
    
    return currency_info_list


def format_currency_info_display(currency_info_list: List[Dict[str, str]]) -> str:
    """
    Format currency information for display.
    
    Args:
        currency_info_list: List of currency information dictionaries
        
    Returns:
        Formatted string for display
    """
    if not currency_info_list:
        return "Нет данных о валютах"
    
    lines = []
    lines.append("Информация о курсах валют:")
    lines.append("=" * 50)
    
    for info in currency_info_list:
        lines.append(f"Валюта: {info['currency']}")
        lines.append(f"  Базовый код: {info['base_code']}")
        lines.append(f"  Последнее обновление: {info['last_update']}")
        lines.append(f"  Следующее обновление: {info['next_update']}")
        lines.append(f"  Провайдер: {info['provider']}")
        lines.append(f"  Количество курсов: {info['rates_count']}")
        lines.append("-" * 30)

    return "\n".join(lines)