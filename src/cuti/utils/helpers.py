"""
Helper functions and utilities for cuti.
"""

import re
from typing import Any


def safe_filename(text: str, max_length: int = 50) -> str:
    """Sanitize text for use in filename.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length of resulting filename
        
    Returns:
        Sanitized filename string
    """
    # Remove invalid filename characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        text = text.replace(char, "-")
    
    # Collapse multiple dashes/spaces into single dash
    text = re.sub(r"[-\s]+", "-", text)
    
    # Remove leading/trailing dashes
    text = text.strip("-")
    
    # Truncate to max length
    return text[:max_length]


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human readable duration string
    """
    if seconds < 0:
        return "now"

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to append when truncating
        
    Returns:
        Truncated text string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def deep_merge(dict1: dict, dict2: dict) -> dict:
    """Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def validate_prompt_content(content: str) -> tuple[bool, str]:
    """Validate prompt content.
    
    Args:
        content: Prompt content to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "Prompt content cannot be empty"
    
    if len(content.strip()) < 10:
        return False, "Prompt content must be at least 10 characters"
    
    return True, ""


def extract_metadata_from_content(content: str) -> dict[str, Any]:
    """Extract metadata from prompt content.
    
    Args:
        content: Prompt content
        
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {}
    
    # Extract estimated tokens if mentioned
    token_pattern = r'(?:approximately|about|~)\s*(\d+)\s*tokens?'
    token_match = re.search(token_pattern, content, re.IGNORECASE)
    if token_match:
        metadata['estimated_tokens'] = int(token_match.group(1))
    
    # Extract priority if mentioned
    priority_pattern = r'priority\s*[:=]\s*(\d+)'
    priority_match = re.search(priority_pattern, content, re.IGNORECASE)
    if priority_match:
        metadata['priority'] = int(priority_match.group(1))
    
    return metadata