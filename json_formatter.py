"""
JSON Formatter Module
Handles JSON formatting and display in human-readable format with color support.
"""

import json
import re
from typing import Any, Dict, List, Union
from colorama import Fore, Style


def format_json_pretty(data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
    """
    Format JSON data in a pretty, human-readable format.
    
    Args:
        data: JSON data to format
        indent: Number of spaces for indentation
        ensure_ascii: Whether to escape non-ASCII characters
        
    Returns:
        Formatted JSON string
    """
    try:
        return json.dumps(data, indent=indent, ensure_ascii=ensure_ascii, sort_keys=True)
    except (TypeError, ValueError) as e:
        return f"Ошибка форматирования JSON: {e}"


def format_json_compact(data: Any) -> str:
    """
    Format JSON data in compact format (single line).
    
    Args:
        data: JSON data to format
        
    Returns:
        Compact JSON string
    """
    try:
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    except (TypeError, ValueError) as e:
        return f"Ошибка форматирования JSON: {e}"


def format_json_table(data: Union[Dict, List], max_depth: int = 3) -> str:
    """
    Format JSON data in a table-like structure for better readability.
    
    Args:
        data: JSON data to format
        max_depth: Maximum nesting depth to display
        
    Returns:
        Formatted table-like string
    """
    if isinstance(data, dict):
        return _format_dict_table(data, max_depth, 0)
    elif isinstance(data, list):
        return _format_list_table(data, max_depth, 0)
    else:
        return str(data)


def _format_dict_table(data: Dict, max_depth: int, current_depth: int) -> str:
    """Format dictionary in table-like structure."""
    if current_depth >= max_depth:
        return f"{{...}} ({len(data)} элементов)"
    
    lines = []
    for key, value in data.items():
        if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
            if isinstance(value, dict):
                lines.append(f"  {'  ' * current_depth}{key}:")
                lines.append(_format_dict_table(value, max_depth, current_depth + 1))
            elif isinstance(value, list):
                lines.append(f"  {'  ' * current_depth}{key}: [{len(value)} элементов]")
                if value and current_depth < max_depth - 1:
                    for i, item in enumerate(value[:3]):  # Show first 3 items
                        if isinstance(item, dict):
                            lines.append(f"    {'  ' * current_depth}[{i}]:")
                            lines.append(_format_dict_table(item, max_depth, current_depth + 1))
                        else:
                            lines.append(f"    {'  ' * current_depth}[{i}]: {item}")
                    if len(value) > 3:
                        lines.append(f"    {'  ' * current_depth}... и еще {len(value) - 3} элементов")
        else:
            formatted_value = _format_value(value, max_depth, current_depth)
            lines.append(f"  {'  ' * current_depth}{key}: {formatted_value}")
    
    return '\n'.join(lines)


def _format_list_table(data: List, max_depth: int, current_depth: int) -> str:
    """Format list in table-like structure."""
    if current_depth >= max_depth:
        return f"[...] ({len(data)} элементов)"
    
    lines = []
    for i, item in enumerate(data[:5]):  # Show first 5 items
        if isinstance(item, dict):
            lines.append(f"  {'  ' * current_depth}[{i}]:")
            lines.append(_format_dict_table(item, max_depth, current_depth + 1))
        elif isinstance(item, list):
            lines.append(f"  {'  ' * current_depth}[{i}]: [{len(item)} элементов]")
            if item and current_depth < max_depth - 1:
                lines.append(_format_list_table(item, max_depth, current_depth + 1))
        else:
            lines.append(f"  {'  ' * current_depth}[{i}]: {item}")
    
    if len(data) > 5:
        lines.append(f"  {'  ' * current_depth}... и еще {len(data) - 5} элементов")
    
    return '\n'.join(lines)


def _format_value(value: Any, max_depth: int, current_depth: int) -> str:
    """Format a single value."""
    if isinstance(value, str):
        # Truncate very long strings
        if len(value) > 100:
            return f'"{value[:97]}..."'
        return f'"{value}"'
    elif isinstance(value, (int, float, bool)):
        return str(value)
    elif value is None:
        return "null"
    elif isinstance(value, (dict, list)):
        if isinstance(value, dict):
            return f"{{...}} ({len(value)} элементов)"
        else:
            return f"[...] ({len(value)} элементов)"
    else:
        return str(value)


def format_json_summary(data: Any) -> str:
    """
    Create a summary of JSON data structure.
    
    Args:
        data: JSON data to summarize
        
    Returns:
        Summary string
    """
    if isinstance(data, dict):
        return f"Объект с {len(data)} полями"
    elif isinstance(data, list):
        return f"Массив с {len(data)} элементами"
    else:
        return f"Значение типа {type(data).__name__}"


def format_json_colorful(data: Any, indent: int = 2) -> str:
    """
    Format JSON data with colorful syntax highlighting.
    
    Args:
        data: JSON data to format
        indent: Number of spaces for indentation
        
    Returns:
        Colorful formatted JSON string
    """
    try:
        json_str = json.dumps(data, indent=indent, ensure_ascii=False, sort_keys=True)
        return _add_json_colors(json_str)
    except (TypeError, ValueError) as e:
        return f"{Fore.RED}Ошибка форматирования JSON: {e}{Style.RESET_ALL}"


def _add_json_colors(json_str: str) -> str:
    """
    Add color highlighting to JSON string.
    
    Args:
        json_str: JSON string to colorize
        
    Returns:
        Colorized JSON string
    """
    # Color scheme
    colors = {
        'key': Fore.CYAN,           # Keys
        'string': Fore.GREEN,       # String values
        'number': Fore.YELLOW,      # Numbers
        'boolean': Fore.MAGENTA,    # true/false
        'null': Fore.RED,           # null
        'punctuation': Fore.WHITE,   # {}, [], :, ,
    }
    
    lines = json_str.split('\n')
    colored_lines = []
    
    for line in lines:
        colored_line = _colorize_json_line(line, colors)
        colored_lines.append(colored_line)
    
    return '\n'.join(colored_lines)


def _colorize_json_line(line: str, colors: Dict[str, str]) -> str:
    """
    Colorize a single JSON line.
    
    Args:
        line: JSON line to colorize
        colors: Color mapping dictionary
        
    Returns:
        Colorized line
    """
    # Remove leading whitespace to work with the content
    stripped = line.lstrip()
    leading_spaces = line[:len(line) - len(stripped)]
    
    if not stripped:
        return line
    
    # Pattern for JSON key-value pairs
    # Match: "key": value
    key_pattern = r'^(\s*)"([^"]+)"(\s*:\s*)'
    
    # Pattern for string values
    string_pattern = r'"([^"]*)"'
    
    # Pattern for numbers
    number_pattern = r'\b(-?\d+\.?\d*)\b'
    
    # Pattern for booleans and null
    boolean_null_pattern = r'\b(true|false|null)\b'
    
    # Pattern for punctuation
    punctuation_pattern = r'([{}[\]])'
    
    result = stripped
    
    # Colorize punctuation first
    result = re.sub(punctuation_pattern, f'{colors["punctuation"]}\\1{Style.RESET_ALL}', result)
    
    # Colorize booleans and null
    result = re.sub(boolean_null_pattern, f'{colors["boolean"]}\\1{Style.RESET_ALL}', result)
    
    # Colorize numbers (but not inside strings)
    result = re.sub(number_pattern, f'{colors["number"]}\\1{Style.RESET_ALL}', result)
    
    # Colorize strings
    result = re.sub(string_pattern, f'{colors["string"]}"\\1"{Style.RESET_ALL}', result)
    
    # Colorize keys (special handling for key-value pairs)
    def colorize_key(match):
        spaces = match.group(1)
        key = match.group(2)
        colon_part = match.group(3)
        return f'{spaces}{colors["key"]}"{key}"{Style.RESET_ALL}{colon_part}'
    
    result = re.sub(key_pattern, colorize_key, result)
    
    return leading_spaces + result


def format_json_colorful_compact(data: Any) -> str:
    """
    Format JSON data in compact format with colors.
    
    Args:
        data: JSON data to format
        
    Returns:
        Colorful compact JSON string
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        return _add_json_colors(json_str)
    except (TypeError, ValueError) as e:
        return f"{Fore.RED}Ошибка форматирования JSON: {e}{Style.RESET_ALL}"


def format_json_colorful_table(data: Union[Dict, List], max_depth: int = 3) -> str:
    """
    Format JSON data in a colorful table-like structure.
    
    Args:
        data: JSON data to format
        max_depth: Maximum nesting depth to display
        
    Returns:
        Colorful formatted table-like string
    """
    if isinstance(data, dict):
        return _format_dict_table_colorful(data, max_depth, 0)
    elif isinstance(data, list):
        return _format_list_table_colorful(data, max_depth, 0)
    else:
        return _colorize_value(data)


def _format_dict_table_colorful(data: Dict, max_depth: int, current_depth: int) -> str:
    """Format dictionary in colorful table-like structure."""
    if current_depth >= max_depth:
        return f"{Fore.CYAN}{{...}}{Style.RESET_ALL} {Fore.YELLOW}({len(data)} элементов){Style.RESET_ALL}"
    
    lines = []
    for key, value in data.items():
        colored_key = f"{Fore.CYAN}{key}{Style.RESET_ALL}"
        if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
            if isinstance(value, dict):
                lines.append(f"  {'  ' * current_depth}{colored_key}:")
                lines.append(_format_dict_table_colorful(value, max_depth, current_depth + 1))
            elif isinstance(value, list):
                lines.append(f"  {'  ' * current_depth}{colored_key}: {Fore.MAGENTA}[{len(value)} элементов]{Style.RESET_ALL}")
                if value and current_depth < max_depth - 1:
                    for i, item in enumerate(value[:3]):  # Show first 3 items
                        if isinstance(item, dict):
                            lines.append(f"    {'  ' * current_depth}{Fore.YELLOW}[{i}]{Style.RESET_ALL}:")
                            lines.append(_format_dict_table_colorful(item, max_depth, current_depth + 1))
                        else:
                            colored_item = _colorize_value(item)
                            lines.append(f"    {'  ' * current_depth}{Fore.YELLOW}[{i}]{Style.RESET_ALL}: {colored_item}")
                    if len(value) > 3:
                        lines.append(f"    {'  ' * current_depth}{Fore.RED}... и еще {len(value) - 3} элементов{Style.RESET_ALL}")
        else:
            formatted_value = _colorize_value(value, max_depth, current_depth)
            lines.append(f"  {'  ' * current_depth}{colored_key}: {formatted_value}")
    
    return '\n'.join(lines)


def _format_list_table_colorful(data: List, max_depth: int, current_depth: int) -> str:
    """Format list in colorful table-like structure."""
    if current_depth >= max_depth:
        return f"{Fore.MAGENTA}[...]{Style.RESET_ALL} {Fore.YELLOW}({len(data)} элементов){Style.RESET_ALL}"
    
    lines = []
    for i, item in enumerate(data[:5]):  # Show first 5 items
        if isinstance(item, dict):
            lines.append(f"  {'  ' * current_depth}{Fore.YELLOW}[{i}]{Style.RESET_ALL}:")
            lines.append(_format_dict_table_colorful(item, max_depth, current_depth + 1))
        elif isinstance(item, list):
            lines.append(f"  {'  ' * current_depth}{Fore.YELLOW}[{i}]{Style.RESET_ALL}: {Fore.MAGENTA}[{len(item)} элементов]{Style.RESET_ALL}")
            if item and current_depth < max_depth - 1:
                lines.append(_format_list_table_colorful(item, max_depth, current_depth + 1))
        else:
            colored_item = _colorize_value(item)
            lines.append(f"  {'  ' * current_depth}{Fore.YELLOW}[{i}]{Style.RESET_ALL}: {colored_item}")
    
    if len(data) > 5:
        lines.append(f"  {'  ' * current_depth}{Fore.RED}... и еще {len(data) - 5} элементов{Style.RESET_ALL}")
    
    return '\n'.join(lines)


def _colorize_value(value: Any, max_depth: int = 3, current_depth: int = 0) -> str:
    """Colorize a single value."""
    if isinstance(value, str):
        # Truncate very long strings
        if len(value) > 100:
            truncated = f'"{value[:97]}..."'
        else:
            truncated = f'"{value}"'
        return f"{Fore.GREEN}{truncated}{Style.RESET_ALL}"
    elif isinstance(value, (int, float)):
        return f"{Fore.YELLOW}{value}{Style.RESET_ALL}"
    elif isinstance(value, bool):
        return f"{Fore.MAGENTA}{value}{Style.RESET_ALL}"
    elif value is None:
        return f"{Fore.RED}null{Style.RESET_ALL}"
    elif isinstance(value, (dict, list)):
        if isinstance(value, dict):
            return f"{Fore.CYAN}{{...}}{Style.RESET_ALL} {Fore.YELLOW}({len(value)} элементов){Style.RESET_ALL}"
        else:
            return f"{Fore.MAGENTA}[...]{Style.RESET_ALL} {Fore.YELLOW}({len(value)} элементов){Style.RESET_ALL}"
    else:
        return f"{Fore.WHITE}{value}{Style.RESET_ALL}"


def format_json_for_display(data: Any, style: str = "pretty") -> str:
    """
    Format JSON data for display with specified style.
    
    Args:
        data: JSON data to format
        style: Display style ("pretty", "compact", "table", "summary", "colorful", "colorful_compact", "colorful_table")
        
    Returns:
        Formatted string for display
    """
    if style == "pretty":
        return format_json_pretty(data)
    elif style == "compact":
        return format_json_compact(data)
    elif style == "table":
        return format_json_table(data)
    elif style == "summary":
        return format_json_summary(data)
    elif style == "colorful":
        return format_json_colorful(data)
    elif style == "colorful_compact":
        return format_json_colorful_compact(data)
    elif style == "colorful_table":
        return format_json_colorful_table(data)
    else:
        return format_json_pretty(data)
