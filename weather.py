import requests
from dotenv import load_dotenv
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OW_API_KEY")
CACHE_DIR = "cache"
GEOCODING_CACHE = os.path.join(CACHE_DIR, "weather_geocoding.json")
CURRENT_CACHE = os.path.join(CACHE_DIR, "weather_current.json")
FORECAST_CACHE = os.path.join(CACHE_DIR, "weather_forecast.json")
AIR_POLLUTION_CACHE = os.path.join(CACHE_DIR, "weather_air_pollution.json") 
COUNT_3_HOURS_FORECAST = 40 # 24 hours / 3 hours = 8 forecasts
COUNT_DAILY_FORECAST = 7 # 7 days

if not OPENWEATHER_API_KEY:
    print("❌ Ошибка: API ключ OpenWeather не найден!")
    print("Создайте файл .env в корне проекта и добавьте:")
    print("OW_API_KEY=ваш_api_ключ")
    exit(1)
else:
    print(f"✅ API ключ загружен: {OPENWEATHER_API_KEY[:8]}...")


AIR_QUALITY_SCALE = [
    {
        "name_ru": "Хорошее",
        "index": 1,
        "pollutants": {
            "SO2": (0, 20),
            "NO2": (0, 40),
            "PM10": (0, 20),
            "PM2_5": (0, 10),
            "O3": (0, 60),
            "CO": (0, 4400),
        }
    },
    {
        "name_ru": "Умеренное",
        "index": 2,
        "pollutants": {
            "SO2": (20, 80),
            "NO2": (40, 70),
            "PM10": (20, 50),
            "PM2_5": (10, 25),
            "O3": (60, 100),
            "CO": (4400, 9400),
        }
    },
    {
        "name_ru": "Среднее",
        "index": 3,
        "pollutants": {
            "SO2": (80, 250),
            "NO2": (70, 150),
            "PM10": (50, 100),
            "PM2_5": (25, 50),
            "O3": (100, 140),
            "CO": (9400, 12400),
        }
    },
    {
        "name_ru": "Плохое",
        "index": 4,
        "pollutants": {
            "SO2": (250, 350),
            "NO2": (150, 200),
            "PM10": (100, 200),
            "PM2_5": (50, 75),
            "O3": (140, 180),
            "CO": (12400, 15400),
        }
    },
    {
        "name_ru": "Очень плохое",
        "index": 5,
        "pollutants": {
            "SO2": (350, float('inf')),
            "NO2": (200, float('inf')),
            "PM10": (200, float('inf')),
            "PM2_5": (75, float('inf')),
            "O3": (180, float('inf')),
            "CO": (15400, float('inf')),
        }
    },
]

def load_cache(cache_file: str) -> Dict:
    """Load cache from specified file."""
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки кэша {cache_file}: {e}")
    return {}


def save_cache(cache_data: Dict, cache_file: str) -> None:
    """Save cache data to specified file."""
    try:
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения кэша {cache_file}: {e}")


def filter_local_names(data: Dict) -> Dict:
    """Filter local_names to keep only RU and EN languages."""
    if 'local_names' in data and isinstance(data['local_names'], dict):
        filtered = {}
        for lang in ['ru', 'en']:
            if lang in data['local_names']:
                filtered[lang] = data['local_names'][lang]
        data['local_names'] = filtered
    return data


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


def get_cities_list(city: str) -> Dict:
    """Get list of cities matching the search query."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    # Make API request
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={OPENWEATHER_API_KEY}"
    success, geo_data = make_api_request_with_retry(url)
    
    if not success:
        return {"error": "Ошибка при поиске города"}
    
    if not geo_data or len(geo_data) == 0:
        return {"error": "Город не найден"}
    
    # Format cities list for display
    cities_list = []
    for entry in geo_data:
        city_name = entry.get('name', '')
        country = entry.get('country', '')
        state = entry.get('state', None)
        display_name = f"{city_name}"
        if state:
            display_name += f", {state}"
        display_name += f", {country}"
        
        cities_list.append({
            "name": city_name,
            "display_name": display_name,
            "country": country,
            "state": state,
            "lat": entry.get("lat"),
            "lon": entry.get("lon"),
            "data": entry
        })
    
    return {"cities": cities_list}


def get_coordinates_by_city(city: str) -> Dict:
    """Get coordinates by city name with caching."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = get_cache_key(city=city)
    cache = load_cache(GEOCODING_CACHE)
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    # Используем геокодинг API для поиска города
    url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit=5&appid={OPENWEATHER_API_KEY}"
    success, geo_data = make_api_request_with_retry(url)
    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return geo_data
    
    if not geo_data or len(geo_data) == 0:
        return {"error": "Город не найден или ошибка геокодирования"}

    # Если найдено несколько городов, даём выбор
    if len(geo_data) > 1:
        print("🔎 Найдено несколько городов. Уточните выбор:")
        for i, entry in enumerate(geo_data, 1):
            city_name = entry.get('name', '')
            country = entry.get('country', '')
            state = entry.get('state', None)
            display_name = f"{city_name}"
            if state:
                display_name += f", {state}"
            display_name += f", {country}"
            print(f"{i}. {display_name}")
        
        while True:
            try:
                user_choice = int(input("Выберите номер города: ")) - 1
                if 0 <= user_choice < len(geo_data):
                    chosen = geo_data[user_choice]
                    break
                else:
                    print("❌ Неверный номер. Попробуйте ещё раз.")
            except Exception:
                print("❌ Неверный ввод. Введите номер из списка.")
    else:
        chosen = geo_data[0]

    # Filter local_names and save to cache
    chosen = filter_local_names(chosen)
    cache[cache_key] = {
        "city": city,
        "lat": chosen.get("lat"),
        "lon": chosen.get("lon"),
        "fetched_at": datetime.now().isoformat(),
        "data": chosen
    }
    save_cache(cache, GEOCODING_CACHE)
    
    return chosen


def get_city_by_coordinates(lat: float, lon: float) -> Dict:
    """Get city by coordinates with caching."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = get_cache_key(lat=lat, lon=lon)
    cache = load_cache(GEOCODING_CACHE)
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    url = f"https://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={OPENWEATHER_API_KEY}"
    success, data = make_api_request_with_retry(url)
    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return data
    
    if not data or len(data) == 0:
        return {"error": "Город не найден или ошибка геокодирования"}
    
    # Filter local_names and save to cache
    data[0] = filter_local_names(data[0])
    cache[cache_key] = {
        "city": data[0].get("name"),
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "data": data[0]
    }
    save_cache(cache, GEOCODING_CACHE)
    
    return data[0]


def get_weather_by_coordinates(lat: float, lon: float) -> Dict:
    """Get weather by coordinates with caching."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = get_cache_key(lat=lat, lon=lon)
    cache = load_cache(CURRENT_CACHE)
    
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
    save_cache(cache, CURRENT_CACHE)
    
    return data


def get_hourly_weather(lat: float, lon: float) -> Dict:
    """Get hourly weather data for a given location."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    # Формируем ключ для кэша, чтобы отделять разные точки и разные длины прогноза:
    # Например, для lat=39.91 и lon=116.39 это будет "hourly:39.91,116.39:40"
    # Такое форматирование помогает хранить отдельные данные прогноза для каждой уникальной локации и длины запроса
    cache_key = f"hourly:{lat:.2f},{lon:.2f}:{COUNT_3_HOURS_FORECAST}"
    cache = load_cache(FORECAST_CACHE)
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&lang=ru&appid={OPENWEATHER_API_KEY}&cnt={COUNT_3_HOURS_FORECAST}"
    success, data = make_api_request_with_retry(url)
    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return data
    
    # Check for API errors
    if data.get("cod") != "200" and data.get("cod") != 200:
        return {"error": data.get("message", f"API error with code: {data.get('cod')}"), "status_code": data.get("cod")}
    
    # Save to cache
    cache[cache_key] = {
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "data": data
    }
    save_cache(cache, FORECAST_CACHE)
    
    return data

def get_daily_weather(lat: float, lon: float) -> Dict:
    """Get daily weather data for a given location using 5-day forecast API."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = f"daily:{lat:.2f},{lon:.2f}:{COUNT_DAILY_FORECAST}"
    cache = load_cache(FORECAST_CACHE)
        
    # Проверяем кэш
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша (ежедневный прогноз)")
        return cache[cache_key]['data']
    
    # Используем стандартный 5-day forecast API и группируем по дням
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&lang=ru&appid={OPENWEATHER_API_KEY}"
    
    success, data = make_api_request_with_retry(url)
    
    if not success:
        # Пробуем достать из кэша при ошибке сети/API
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем daily forecast из кэша")
            return cache[cache_key]['data']
        return data

    # Проверяем на ошибку API
    if data.get("cod") != "200" and data.get("cod") != 200:
        return {"error": data.get("message", f"API error with code: {data.get('cod')}"), "status_code": data.get("cod")}
    
    # Группируем прогнозы по дням (берем прогноз на 12:00 каждого дня)
    daily_forecasts = []
    forecasts = data.get("list", [])
    
    # Группируем по дням и берем прогноз на 12:00 (или ближайший к нему)
    current_date = None
    for forecast in forecasts:
        dt = datetime.fromtimestamp(forecast.get("dt", 0))
        forecast_date = dt.date()
        
        if current_date != forecast_date:
            current_date = forecast_date
            # Берем прогноз на 12:00 или ближайший к нему
            target_hour = 12
            best_forecast = None
            min_diff = float('inf')
            
            for f in forecasts:
                f_dt = datetime.fromtimestamp(f.get("dt", 0))
                if f_dt.date() == forecast_date:
                    hour_diff = abs(f_dt.hour - target_hour)
                    if hour_diff < min_diff:
                        min_diff = hour_diff
                        best_forecast = f
            
            if best_forecast:
                daily_forecasts.append(best_forecast)
                
                if len(daily_forecasts) >= COUNT_DAILY_FORECAST:
                    break
    
    # Создаем структуру данных аналогичную старому API
    daily_data = {
        "city": data.get("city", {}),
        "list": daily_forecasts
    }
    
    # Сохраняем данные в кэш
    cache[cache_key] = {
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "data": daily_data
    }
    save_cache(cache, FORECAST_CACHE)
    
    return daily_data


def get_daily_weather_by_city(city: str) -> Dict:
    """Get daily weather by city name - first get coordinates, then daily forecast."""
    # Get city coordinates
    coords_data = get_coordinates_by_city(city)
    if "error" in coords_data:
        return coords_data
    
    lat = coords_data.get("lat")
    lon = coords_data.get("lon")
    
    if lat is None or lon is None:
        return {"error": "Не удалось получить координаты города"}
    
    # Get daily forecast by coordinates
    return get_daily_weather(lat, lon)
    
def get_weather_by_city(city: str) -> Dict:
    """Get weather by city name - сначала получаем координаты, потом погоду."""
    # Получаем координаты города
    coords_data = get_coordinates_by_city(city)
    if "error" in coords_data:
        return coords_data
    
    lat = coords_data.get("lat")
    lon = coords_data.get("lon")
    
    if lat is None or lon is None:
        return {"error": "Не удалось получить координаты города"}
    
    # Получаем погоду по координатам
    return get_weather_by_coordinates(lat, lon)


def get_hourly_weather_by_city(city: str) -> Dict:
    """Get hourly weather by city name - first get coordinates, then forecast."""
    # Get city coordinates
    coords_data = get_coordinates_by_city(city)
    if "error" in coords_data:
        return coords_data
    
    lat = coords_data.get("lat")
    lon = coords_data.get("lon")
    
    if lat is None or lon is None:
        return {"error": "Не удалось получить координаты города"}
    
    # Get hourly forecast by coordinates
    return get_hourly_weather(lat, lon)


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
        
        return f"""<code>📍 Место:       {location}</code>
<code>🌡️ Температура: {temp:.1f}°C</code>
<code>💧 Влажность:   {humidity}%</code>
<code>🌬️ Ветер:       {wind_speed} м/с, {wind_dir}</code>
<code>☁️ Погода:      {weather_desc.title()}</code>"""
    except Exception as e:
        return f"❌ Ошибка форматирования данных: {e}"


def format_hourly_weather(data: Dict) -> str:
    """Format hourly weather data for display."""
    if "error" in data:
        return f"❌ Ошибка: {data['error']}"
    
    try:
        city = data.get("city", {}).get("name", "Неизвестно")
        country = data.get("city", {}).get("country", "")
        if country:
            city += f", {country}"
        
        result = f"📍 Место: {city}\n"
        result += f"📅 Прогноз {COUNT_3_HOURS_FORECAST * 3} часов (3-часовые интервалы):\n\n"
        result += f"<code>{"Дата/Время":<11} | {"Темп.":<7} | {"Вл.":<4} | {"Ветер":<9} | {"Погода":<15}</code>\n"
        result += "<code>" + "-"*56 + "</code>\n"
        forecasts = data.get("list", [])
        for i, forecast in enumerate(forecasts[:COUNT_3_HOURS_FORECAST]):  # Show first COUNT_3_HOURS_FORECAST forecasts
            dt = datetime.fromtimestamp(forecast.get("dt", 0))
            temp = forecast.get("main", {}).get("temp", 0)
            humidity = forecast.get("main", {}).get("humidity", 0)
            wind_speed = forecast.get("wind", {}).get("speed", 0)
            weather_desc = forecast.get("weather", [{}])[0].get("description", "Неизвестно")
            
            # Форматирование с фиксированной шириной столбцов
            date_time = dt.strftime('%d.%m %H:%M')
            temp_str = f"{temp:.1f}°C"
            humidity_str = f"{humidity}%"
            wind_str = f"{wind_speed:.1f} м/с"
            weather_str = weather_desc.title()
            
            result += f"<code>{date_time:<10} | {temp_str:<7} | {humidity_str:<4} | {wind_str:<9} | {weather_str:<15}</code>\n"
        
        return result
    except Exception as e:
        return f"❌ Ошибка форматирования данных: {e}"
        
def format_daily_weather(data: Dict) -> str:
    """Format daily weather data for display."""
    if "error" in data:
        return f"❌ Ошибка: {data['error']}"
    
    try:
        city = data.get("city", {}).get("name", "Неизвестно")
        country = data.get("city", {}).get("country", "")
        if country:
            city += f", {country}"
        
        result = f"📍 Место: {city}\n"
        result += f"📅 Прогноз {COUNT_DAILY_FORECAST} дней (ежедневные интервалы):\n\n"
        result += f"<code>{"Дата":<10} | {"Темп.":<7} | {"Вл.":<4} | {"Ветер":<9} | {"Погода":<15}</code>\n"
        result += "<code>" + "-"*56 + "</code>\n"
        forecasts = data.get("list", [])
        for i, forecast in enumerate(forecasts[:COUNT_DAILY_FORECAST]):
            dt = datetime.fromtimestamp(forecast.get("dt", 0))
            temp = forecast.get("main", {}).get("temp", 0)  # Используем main.temp вместо temp.day
            humidity = forecast.get("main", {}).get("humidity", 0)  # Используем main.humidity
            wind_speed = forecast.get("wind", {}).get("speed", 0)  # Используем wind.speed
            weather_desc = forecast.get("weather", [{}])[0].get("description", "Неизвестно")
            
            # Форматирование с фиксированной шириной столбцов
            date_time = dt.strftime('%d.%m')
            temp_str = f"{temp:.1f}°C"
            humidity_str = f"{humidity}%"
            wind_str = f"{wind_speed:.1f} м/с"
            weather_str = weather_desc.title()
            
            result += f"<code>{date_time:<10} | {temp_str:<7} | {humidity_str:<4} | {wind_str:<9} | {weather_str:<15}</code>\n"
        
        return result
    except Exception as e:
        return f"❌ Ошибка форматирования данных: {e}"

def get_air_pollution(lat: float, lon: float) -> Dict:
    """Get air pollution data for a given location."""
    if not OPENWEATHER_API_KEY:
        return {"error": "API ключ OpenWeather не настроен"}
    
    cache_key = f"air_pollution:{lat:.2f},{lon:.2f}"
    cache = load_cache(AIR_POLLUTION_CACHE)
    
    # Check cache first
    if cache_key in cache and is_cache_valid(cache[cache_key]):
        print("📦 Используем данные из кэша")
        return cache[cache_key]['data']
    
    # Make API request
    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"
    success, data = make_api_request_with_retry(url)    
    if not success:
        # Try to use cache if API fails
        if cache_key in cache:
            print("🌐 Сетевая ошибка. Используем данные из кэша:")
            return cache[cache_key]['data']
        return data
    
    if not data or len(data) == 0:
        return {"error": "Не удалось получить данные о загрязнении воздуха"}
    
    # Save to cache
    cache[cache_key] = {
        "lat": lat,
        "lon": lon,
        "fetched_at": datetime.now().isoformat(),
        "data": data
    }
    save_cache(cache, AIR_POLLUTION_CACHE)
    
    return data

def get_air_pollution_by_city(city: str) -> Dict:
    """Get air pollution data by city name - first get coordinates, then pollution data."""
    # Get city coordinates
    coords_data = get_coordinates_by_city(city)
    if "error" in coords_data:
        return coords_data
    
    lat = coords_data.get("lat")
    lon = coords_data.get("lon")
    
    if lat is None or lon is None:
        return {"error": "Не удалось получить координаты города"}
    
    # Get air pollution by coordinates
    return get_air_pollution(lat, lon)

def get_air_quality_level(pollutant_type: str, concentration: float) -> str:
    """
    Определяет уровень качества воздуха для заданной концентрации загрязнителя
    на основе шкалы OpenWeather.
    
    Args:
        pollutant_type (str): Тип загрязнителя (например, "SO2", "PM2.5")
        concentration (float): Концентрация загрязнителя
        
    Returns:
        str: Качественный уровень качества воздуха на русском языке
    """
    pollutant_type = pollutant_type.upper()
    
    # Преобразуем PM2.5 в PM2_5 для соответствия с AIR_QUALITY_SCALE
    if pollutant_type == "PM2.5":
        pollutant_type = "PM2_5"
    
    for level in AIR_QUALITY_SCALE:
        if pollutant_type in level["pollutants"]:
            min_val, max_val = level["pollutants"][pollutant_type]
            
            # Проверяем, попадает ли концентрация в диапазон [min_val; max_val)
            if min_val <= concentration < max_val:
                return level["name_ru"]
    
    return "Неизвестно"

def analyze_air_pollution(data: Dict) -> str:
    """Анализирует данные о загрязнении воздуха и возвращает форматированный отчет."""
    if "error" in data:
        return f"❌ Ошибка: {data['error']}"
    
    try:
        # Получаем данные о загрязнении
        air_pollution = data.get("list", [])
        if not air_pollution:
            return "❌ Нет данных о загрязнении воздуха"
        
        # Берем последние данные
        latest_data = air_pollution[-1]
        components = latest_data.get("components", {})
        
        if not components:
            return "❌ Нет данных о компонентах загрязнения"
        
        result = "🌬️ Анализ качества воздуха:\n\n"
        
        # Анализируем каждый компонент
        pollutants = {
            "so2": "Диоксид серы",
            "no2": "Диоксид азота", 
            "pm10": "PM₁₀ (взвешенные частицы)",
            "pm2_5": "PM₂.₅ (мелкие частицы)",
            "o3": "Озон",
            "co": "Оксид углерода"
        }
        
        result += "<code>"
        for pollutant_code, pollutant_name in pollutants.items():
            concentration = components.get(pollutant_code, 0)
            quality_level = get_air_quality_level(pollutant_code.upper(), concentration)
            
            # Форматируем концентрацию
            if pollutant_code == "co":
                # CO в мкг/м³, но обычно показывают в мг/м³
                concentration_display = f"{concentration:.1f}"
                unit = "мкг/м³"
            else:
                concentration_display = f"{concentration:.1f}"
                unit = "мкг/м³"
            
            result += f"{pollutant_name:<25}: {concentration_display:<8} {unit:<8} - {quality_level}\n"
        
        # Общий индекс качества воздуха (AQI)
        aqi = latest_data.get("main", {}).get("aqi", 0)
        aqi_levels = {1: "Хорошее", 2: "Умеренное", 3: "Среднее", 4: "Плохое", 5: "Очень плохое"}
        overall_quality = aqi_levels.get(aqi, "Неизвестно")
        
        result += f"\n📊 Общий индекс качества воздуха (AQI): {aqi} - {overall_quality}"
        result += "</code>"
        
        return result
        
    except Exception as e:
        return f"❌ Ошибка анализа данных: {e}"
# Test functions
if __name__ == "__main__":
    print("Тестирование погоды по городу:")
    result = get_weather_by_city("London")
    print(format_weather_data(result))
    print ("Тестирование погоды по часам:")
    result = get_hourly_weather_by_city("London")
    print(format_hourly_weather(result))
    print("Тестирование загрязнения воздуха:")
    result = get_air_pollution_by_city("London") 
    print(analyze_air_pollution(result))