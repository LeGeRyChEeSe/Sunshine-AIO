"""
Translation System for Sunshine-AIO GUI

Provides dynamic language switching with hot-reload capability.
"""

import json
import os
from typing import Dict, Any, Optional, Callable
from enum import Enum


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    FRENCH = "fr"
    SPANISH = "es"
    GERMAN = "de"
    ITALIAN = "it"
    JAPANESE = "ja"


class TranslationManager:
    """Manages translations and language switching"""
    
    def __init__(self):
        self.current_language = Language.ENGLISH
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.observers: list[Callable] = []
        self._load_all_translations()
    
    def _load_all_translations(self):
        """Load all translation files"""
        translations_dir = os.path.join(os.path.dirname(__file__), "languages")
        
        for language in Language:
            file_path = os.path.join(translations_dir, f"{language.value}.json")
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.translations[language.value] = json.load(f)
                else:
                    # Fallback to English if file doesn't exist
                    self.translations[language.value] = self.translations.get('en', {})
            except Exception as e:
                print(f"Warning: Failed to load {language.value} translations: {e}")
                self.translations[language.value] = {}
    
    def set_language(self, language: Language):
        """Change the current language"""
        if language != self.current_language:
            self.current_language = language
            self._notify_observers()
    
    def get_current_language(self) -> Language:
        """Get current language"""
        return self.current_language
    
    def get_available_languages(self) -> list[Language]:
        """Get list of available languages"""
        return list(Language)
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Translate a key to current language with optional formatting
        
        Args:
            key: Translation key (dot-separated for nested keys)
            **kwargs: Format arguments for string formatting
        
        Returns:
            Translated string or key if not found
        """
        try:
            current_translations = self.translations.get(self.current_language.value, {})
            
            # Handle nested keys like "main.install_button"
            keys = key.split('.')
            value = current_translations
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    # Fallback to English
                    english_translations = self.translations.get('en', {})
                    value = english_translations
                    for k in keys:
                        if isinstance(value, dict) and k in value:
                            value = value[k]
                        else:
                            return key  # Return key if not found
                    break
            
            if isinstance(value, str):
                # Format string with provided arguments
                return value.format(**kwargs) if kwargs else value
            else:
                return key
                
        except Exception:
            return key
    
    def add_observer(self, callback: Callable):
        """Add observer for language changes"""
        self.observers.append(callback)
    
    def remove_observer(self, callback: Callable):
        """Remove observer"""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def _notify_observers(self):
        """Notify all observers of language change"""
        for callback in self.observers:
            try:
                callback()
            except Exception as e:
                print(f"Error notifying translation observer: {e}")


# Global translation manager instance
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """Get the global translation manager instance"""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def t(key: str, **kwargs) -> str:
    """Shorthand function for translation"""
    return get_translation_manager().translate(key, **kwargs)


def set_language(language: Language):
    """Set current language"""
    get_translation_manager().set_language(language)


def get_current_language() -> Language:
    """Get current language"""
    return get_translation_manager().get_current_language()


def add_translation_observer(callback: Callable):
    """Add observer for language changes"""
    get_translation_manager().add_observer(callback)


def remove_translation_observer(callback: Callable):
    """Remove translation observer"""
    get_translation_manager().remove_observer(callback)