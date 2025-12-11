# Prompt Loader with Hot-Reload
# Loads prompts from YAML files and caches them
# Re-reads file on modification for development workflow

import os
import yaml
from typing import Dict, Any, Optional
from functools import lru_cache


# Cache for loaded prompts
_prompt_cache: Dict[str, Dict[str, Any]] = {}
_file_mtimes: Dict[str, float] = {}

# Base path for prompts
PROMPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_prompt_path(category: str) -> str:
    """Get full path to a prompt YAML file"""
    return os.path.join(PROMPTS_DIR, f"{category}.yaml")


def _load_yaml_file(path: str) -> Dict[str, Any]:
    """Load YAML file with error handling"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"⚠️ Prompt file not found: {path}")
        return {}
    except yaml.YAMLError as e:
        print(f"⚠️ YAML error in {path}: {e}")
        return {}


def _check_file_changed(path: str) -> bool:
    """Check if file has been modified since last load"""
    try:
        current_mtime = os.path.getmtime(path)
        if path not in _file_mtimes:
            return True
        return current_mtime != _file_mtimes[path]
    except OSError:
        return True


def get_prompt(category: str, name: str, **kwargs) -> str:
    """
    Load a prompt from YAML with hot-reload support.
    
    Args:
        category: The prompt category (agent, memory, evaluation)
        name: The prompt name within the category
        **kwargs: Variables to format into the prompt
    
    Returns:
        Formatted prompt string
    
    Example:
        prompt = get_prompt("agent", "system_prompt", workspace="/path")
    """
    path = _get_prompt_path(category)
    
    # Check for hot-reload
    if _check_file_changed(path) or category not in _prompt_cache:
        _prompt_cache[category] = _load_yaml_file(path)
        try:
            _file_mtimes[path] = os.path.getmtime(path)
        except OSError:
            pass
    
    # Get prompt template
    template = _prompt_cache.get(category, {}).get(name, "")
    
    if not template:
        print(f"⚠️ Prompt not found: {category}.{name}")
        return ""
    
    # Format with provided kwargs
    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError as e:
        print(f"⚠️ Missing variable in prompt {category}.{name}: {e}")
        return template


def get_all_prompts(category: str) -> Dict[str, str]:
    """Get all prompts in a category"""
    path = _get_prompt_path(category)
    
    if _check_file_changed(path) or category not in _prompt_cache:
        _prompt_cache[category] = _load_yaml_file(path)
        try:
            _file_mtimes[path] = os.path.getmtime(path)
        except OSError:
            pass
    
    return _prompt_cache.get(category, {})


def reload_prompts():
    """Force reload all prompts (clear cache)"""
    global _prompt_cache, _file_mtimes
    _prompt_cache = {}
    _file_mtimes = {}
    print("🔄 Prompts cache cleared - will reload on next access")


def list_available_prompts() -> Dict[str, list]:
    """List all available prompts by category"""
    result = {}
    for filename in os.listdir(PROMPTS_DIR):
        if filename.endswith('.yaml'):
            category = filename[:-5]  # Remove .yaml
            prompts = get_all_prompts(category)
            result[category] = list(prompts.keys())
    return result
