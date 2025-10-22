"""
HTTP API Client Module
Handles GET and POST requests with error handling and structured responses.
"""

import requests
import json
from typing import Dict, Any, Optional, Tuple


def make_get_request(url: str, params: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any], str]:
    """
    Make a GET request to the specified URL.
    
    Args:
        url: The URL to make the request to
        params: Optional query parameters as a dictionary
        
    Returns:
        Tuple of (status_code, response_data, error_message)
        - status_code: HTTP status code
        - response_data: Parsed JSON data or empty dict
        - error_message: Error message if any, empty string if success
    """
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        try:
            data = response.json()
            return response.status_code, data, ""
        except json.JSONDecodeError:
            return response.status_code, {"raw_text": response.text}, ""
            
    except requests.exceptions.Timeout:
        return 0, {}, "Ошибка: Превышено время ожидания запроса"
    except requests.exceptions.ConnectionError:
        return 0, {}, "Ошибка: Не удалось подключиться к серверу"
    except requests.exceptions.HTTPError as e:
        return response.status_code, {}, f"HTTP ошибка: {e}"
    except Exception as e:
        return 0, {}, f"Неожиданная ошибка: {e}"


def make_post_request(url: str, data: Optional[Dict[str, Any]] = None, 
                     params: Optional[Dict[str, str]] = None) -> Tuple[int, Dict[str, Any], str]:
    """
    Make a POST request to the specified URL.
    
    Args:
        url: The URL to make the request to
        data: Optional POST data as a dictionary
        params: Optional query parameters as a dictionary
        
    Returns:
        Tuple of (status_code, response_data, error_message)
        - status_code: HTTP status code
        - response_data: Parsed JSON data or empty dict
        - error_message: Error message if any, empty string if success
    """
    try:
        response = requests.post(url, json=data, params=params, timeout=10)
        response.raise_for_status()
        
        try:
            response_data = response.json()
            return response.status_code, response_data, ""
        except json.JSONDecodeError:
            return response.status_code, {"raw_text": response.text}, ""
            
    except requests.exceptions.Timeout:
        return 0, {}, "Ошибка: Превышено время ожидания запроса"
    except requests.exceptions.ConnectionError:
        return 0, {}, "Ошибка: Не удалось подключиться к серверу"
    except requests.exceptions.HTTPError as e:
        return response.status_code, {}, f"HTTP ошибка: {e}"
    except Exception as e:
        return 0, {}, f"Неожиданная ошибка: {e}"


def parse_query_params(params_string: str) -> Dict[str, str]:
    """
    Parse query parameters from a string format 'key1=value1,key2=value2'.
    
    Args:
        params_string: String with parameters in format 'key=value,key=value'
        
    Returns:
        Dictionary with parsed parameters
    """
    if not params_string.strip():
        return {}
    
    params = {}
    try:
        pairs = params_string.split(',')
        for pair in pairs:
            if '=' in pair:
                key, value = pair.strip().split('=', 1)
                params[key.strip()] = value.strip()
    except Exception:
        pass
    
    return params
