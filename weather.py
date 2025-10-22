import requests
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OW_API_KEY")
CACHE_FILE = "weather_cache.json"

if not OPENWEATHER_API_KEY:
    print("❌ Ошибка: API ключ OpenWeather не найден!")
    print("Создайте файл .env в корне проекта и добавьте:")
    print("OW_API_KEY=ваш_api_ключ")
    exit(1)
else:
    print(f"✅ API ключ загружен: {OPENWEATHER_API_KEY[:8]}...")


def load_cache() -> Dict:
    """Load weather cache from file."""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки кэша: {e}")
    return {}


def save_cache(cache_data: Dict) -> None:
    """Save weather cache to file."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения кэша: {e}")


def is_cache_valid(cache_entry: Dict) -> bool:
    """Check if cache entry is valid (less than 3 hours old)."""
    if not cache_entry or 'fetched_at' not in cache_entry:
        return False
    
    try:
        fetched_time = datetime.fromisoformat(cache_entry['fetched_at'])
        return datetime.now() - fetched_time < timedelta(hours=3)
    except:
        return False


def get_cache_key(city: str = None, lat: float = None, lon: float = None) -> str:
    """Generate cache key based on location."""
    if city:
        return f"city:{city.lower()}"
    elif lat is not None and lon is not None:
        return f"coords:{lat:.2f},{lon:.2f}"
    return ""


def make_api_request_with_retry(url: str, max_retries: int = 3) -> Tuple[bool, Dict]:
    """Make API request with exponential backoff retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 429:  # Rate limit
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    print(f"Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    return False, {"error": "Rate limit exceeded after retries"}
            
            response.raise_for_status()
            return True, response.json()
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Timeout. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return False, {"error": "Request timeout after retries"}
                
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Connection error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                return False, {"error": "Connection failed after retries"}
                
        except requests.exceptions.RequestException as e:
            return False, {"error": f"Request failed: {str(e)}"}
    
    return False, {"error": "Max retries exceeded"}


def get_weather_by_city(city: str) -> Dict:
    """Get weather by city name with caching."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = get_cache_key(city=city)
    cache = load_cache()
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&lang=ru&appid={OPENWEATHER_API_KEY}"
    success, data = make_api_request_with_retry(url)
    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return data
    
    # Check for API errors
    if data.get("cod") != 200:
        return {"error": data.get("message", "Unknown error from API"), "status_code": data.get("cod")}
    
    # Save to cache
    cache[cache_key] = {
        "city": city,
        "lat": data.get("coord", {}).get("lat"),
        "lon": data.get("coord", {}).get("lon"),
        "fetched_at": datetime.now().isoformat(),
        "data": data
    }
    save_cache(cache)
    
    return data


def get_weather_by_coordinates(lat: float, lon: float) -> Dict:
    """Get weather by coordinates with caching."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = get_cache_key(lat=lat, lon=lon)
    cache = load_cache()
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&lang=ru&appid={OPENWEATHER_API_KEY}"
    success, data = make_api_request_with_retry(url)
    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return data
    
    # Check for API errors
    if data.get("cod") != 200:
        return {"error": data.get("message", "Unknown error from API"), "status_code": data.get("cod")}
    
    # Save to cache
    cache[cache_key] = {
        "city": data.get("name"),
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "data": data
    }
    save_cache(cache)
    
    return data


def format_weather_data(data: Dict) -> str:
    """Format weather data for display."""
    if "error" in data:
        return f"❌ Ошибка: {data['error']}"
    
    try:
        location = data.get("name", "Неизвестно")
        country = data.get("sys", {}).get("country", "")
        if country:
            location += f", {country}"
        
        temp = data.get("main", {}).get("temp", 0)
        humidity = data.get("main", {}).get("humidity", 0)
        
        wind_speed = data.get("wind", {}).get("speed", 0)
        wind_deg = data.get("wind", {}).get("deg", 0)
        
        # Convert wind direction
        wind_directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
        wind_dir = wind_directions[int((wind_deg + 22.5) / 45) % 8] if wind_deg is not None else "?"
        
        weather_desc = data.get("weather", [{}])[0].get("description", "Неизвестно")
        
        return f"""
📍 Место: {location}
🌡️ Температура: {temp:.1f}°C
💧 Влажность: {humidity}%
🌬️ Ветер: {wind_speed} м/с, {wind_dir}
☁️ Погода: {weather_desc.title()}
"""
    except Exception as e:
        return f"❌ Ошибка форматирования данных: {e}"


# Test functions
if __name__ == "__main__":
    print("Тестирование погоды по городу:")
    result = get_weather_by_city("London")
    print(format_weather_data(result))