"""
Advanced Configuration Manager for Sunshine-AIO Community Library

This module provides comprehensive configuration management for library features
including user preferences, security settings, and import/export functionality.
"""

import os
import json
import threading
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

from misc.Logger import log_info, log_error, log_warning, log_success


class LibraryConfigManager:
    """
    Advanced configuration management for library features with validation,
    backup/restore capabilities, and secure preference handling.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize the configuration manager.
        
        Args:
            base_path: Base path for storing configuration files
        """
        self.base_path = base_path
        self.config_dir = os.path.join(base_path, "user_data", "library", "config")
        self.config_file = os.path.join(self.config_dir, "library_config.json")
        self.backup_dir = os.path.join(self.config_dir, "backups")
        
        # Configuration sections
        self._config_sections = {
            'user_preferences': {},
            'search_preferences': {},
            'display_preferences': {},
            'security_preferences': {},
            'library_settings': {},
            'advanced_settings': {}
        }
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Configuration schema for validation
        self._config_schema = self._initialize_config_schema()
        
        # Default configurations
        self._default_config = self._initialize_default_config()
        
        # Current configuration
        self._current_config = {}
        
        # Configuration metadata
        self._config_metadata = {
            'version': '1.0',
            'created_at': None,
            'last_modified': None,
            'backup_count': 0
        }
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing configuration
        self._load_configuration()
        
        log_info("LibraryConfigManager initialized")
    
    def get_user_preferences(self) -> dict:
        """
        Get user preferences section.
        
        Returns:
            Dictionary of user preferences
        """
        try:
            with self._lock:
                return self._current_config.get('user_preferences', {}).copy()
        except Exception as e:
            log_error(f"Error getting user preferences: {e}")
            return self._default_config['user_preferences'].copy()
    
    def set_user_preference(self, key: str, value: Any) -> bool:
        """
        Set a user preference.
        
        Args:
            key: Preference key
            value: Preference value
            
        Returns:
            True if preference was set successfully
        """
        try:
            if not self._validate_preference('user_preferences', key, value):
                log_warning(f"Invalid preference value for {key}: {value}")
                return False
            
            with self._lock:
                if 'user_preferences' not in self._current_config:
                    self._current_config['user_preferences'] = {}
                
                old_value = self._current_config['user_preferences'].get(key)
                self._current_config['user_preferences'][key] = value
                
                # Save configuration
                success = self._save_configuration()
                
                if success:
                    log_info(f"Updated user preference {key}: {old_value} -> {value}")
                else:
                    # Rollback on save failure
                    if old_value is not None:
                        self._current_config['user_preferences'][key] = old_value
                    else:
                        self._current_config['user_preferences'].pop(key, None)
                    log_error(f"Failed to save user preference {key}")
                
                return success
                
        except Exception as e:
            log_error(f"Error setting user preference {key}: {e}")
            return False
    
    def get_search_preferences(self) -> dict:
        """
        Get search preferences section.
        
        Returns:
            Dictionary of search preferences
        """
        try:
            with self._lock:
                return self._current_config.get('search_preferences', {}).copy()
        except Exception as e:
            log_error(f"Error getting search preferences: {e}")
            return self._default_config['search_preferences'].copy()
    
    def get_display_preferences(self) -> dict:
        """
        Get display preferences section.
        
        Returns:
            Dictionary of display preferences
        """
        try:
            with self._lock:
                return self._current_config.get('display_preferences', {}).copy()
        except Exception as e:
            log_error(f"Error getting display preferences: {e}")
            return self._default_config['display_preferences'].copy()
    
    def get_security_preferences(self) -> dict:
        """
        Get security preferences section.
        
        Returns:
            Dictionary of security preferences
        """
        try:
            with self._lock:
                return self._current_config.get('security_preferences', {}).copy()
        except Exception as e:
            log_error(f"Error getting security preferences: {e}")
            return self._default_config['security_preferences'].copy()
    
    def set_preference(self, section: str, key: str, value: Any) -> bool:
        """
        Set a preference in a specific section.
        
        Args:
            section: Configuration section name
            key: Preference key
            value: Preference value
            
        Returns:
            True if preference was set successfully
        """
        try:
            if section not in self._config_sections:
                log_warning(f"Unknown configuration section: {section}")
                return False
            
            if not self._validate_preference(section, key, value):
                log_warning(f"Invalid preference value for {section}.{key}: {value}")
                return False
            
            with self._lock:
                if section not in self._current_config:
                    self._current_config[section] = {}
                
                old_value = self._current_config[section].get(key)
                self._current_config[section][key] = value
                
                # Save configuration
                success = self._save_configuration()
                
                if success:
                    log_info(f"Updated {section}.{key}: {old_value} -> {value}")
                else:
                    # Rollback on save failure
                    if old_value is not None:
                        self._current_config[section][key] = old_value
                    else:
                        self._current_config[section].pop(key, None)
                    log_error(f"Failed to save preference {section}.{key}")
                
                return success
                
        except Exception as e:
            log_error(f"Error setting preference {section}.{key}: {e}")
            return False
    
    def get_preference(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a preference from a specific section.
        
        Args:
            section: Configuration section name
            key: Preference key
            default: Default value if preference not found
            
        Returns:
            Preference value or default
        """
        try:
            with self._lock:
                section_config = self._current_config.get(section, {})
                return section_config.get(key, default)
        except Exception as e:
            log_error(f"Error getting preference {section}.{key}: {e}")
            return default
    
    def reset_to_defaults(self, section: str = None) -> bool:
        """
        Reset configuration to defaults.
        
        Args:
            section: Specific section to reset (None for all sections)
            
        Returns:
            True if reset was successful
        """
        try:
            with self._lock:
                # Create backup before reset
                backup_path = self._create_backup()
                if not backup_path:
                    log_warning("Failed to create backup before reset")
                
                if section:
                    if section in self._default_config:
                        self._current_config[section] = self._default_config[section].copy()
                        log_info(f"Reset {section} to defaults")
                    else:
                        log_warning(f"Unknown section for reset: {section}")
                        return False
                else:
                    self._current_config = self._deep_copy_config(self._default_config)
                    log_info("Reset all configuration to defaults")
                
                # Save reset configuration
                success = self._save_configuration()
                
                if success:
                    log_success("Configuration reset completed")
                else:
                    log_error("Failed to save reset configuration")
                
                return success
                
        except Exception as e:
            log_error(f"Error resetting configuration: {e}")
            return False
    
    def export_config(self, file_path: str) -> bool:
        """
        Export configuration to a file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if export was successful
        """
        try:
            # Ensure export directory exists
            export_dir = os.path.dirname(file_path)
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)
            
            with self._lock:
                export_data = {
                    'export_info': {
                        'version': self._config_metadata['version'],
                        'exported_at': datetime.now().isoformat(),
                        'exported_from': self.base_path
                    },
                    'configuration': self._current_config.copy(),
                    'metadata': self._config_metadata.copy()
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            log_success(f"Exported configuration to {file_path}")
            return True
            
        except Exception as e:
            log_error(f"Error exporting configuration: {e}")
            return False
    
    def import_config(self, file_path: str) -> bool:
        """
        Import configuration from a file.
        
        Args:
            file_path: Path to import file
            
        Returns:
            True if import was successful
        """
        try:
            if not os.path.exists(file_path):
                log_error(f"Import file not found: {file_path}")
                return False
            
            # Create backup before import
            backup_path = self._create_backup()
            if not backup_path:
                log_warning("Failed to create backup before import")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data
            if not self._validate_import_data(import_data):
                log_error("Invalid import data format")
                return False
            
            with self._lock:
                imported_config = import_data.get('configuration', {})
                
                # Validate imported configuration
                if not self._validate_configuration(imported_config):
                    log_error("Imported configuration failed validation")
                    return False
                
                # Merge with current configuration
                self._current_config = self._merge_configurations(
                    self._current_config, 
                    imported_config
                )
                
                # Update metadata
                self._config_metadata['last_modified'] = datetime.now().isoformat()
                
                # Save imported configuration
                success = self._save_configuration()
                
                if success:
                    log_success(f"Imported configuration from {file_path}")
                else:
                    log_error("Failed to save imported configuration")
                
                return success
                
        except Exception as e:
            log_error(f"Error importing configuration: {e}")
            return False
    
    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the current configuration.
        
        Returns:
            Path to backup file if successful, None otherwise
        """
        try:
            return self._create_backup()
        except Exception as e:
            log_error(f"Error creating configuration backup: {e}")
            return None
    
    def restore_backup(self, backup_file: str) -> bool:
        """
        Restore configuration from a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if restore was successful
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_file)
            if not os.path.exists(backup_path):
                log_error(f"Backup file not found: {backup_path}")
                return False
            
            return self.import_config(backup_path)
            
        except Exception as e:
            log_error(f"Error restoring backup: {e}")
            return False
    
    def list_backups(self) -> List[dict]:
        """
        List available configuration backups.
        
        Returns:
            List of backup information dictionaries
        """
        try:
            backups = []
            
            if not os.path.exists(self.backup_dir):
                return backups
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.json'):
                    backup_path = os.path.join(self.backup_dir, filename)
                    
                    try:
                        stat = os.stat(backup_path)
                        backup_info = {
                            'filename': filename,
                            'path': backup_path,
                            'size': stat.st_size,
                            'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                            'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                        }
                        
                        # Try to read backup metadata
                        try:
                            with open(backup_path, 'r', encoding='utf-8') as f:
                                backup_data = json.load(f)
                                backup_info['version'] = backup_data.get('export_info', {}).get('version', 'unknown')
                        except:
                            backup_info['version'] = 'unknown'
                        
                        backups.append(backup_info)
                        
                    except Exception as e:
                        log_warning(f"Error reading backup info for {filename}: {e}")
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            return backups
            
        except Exception as e:
            log_error(f"Error listing backups: {e}")
            return []
    
    def get_configuration_summary(self) -> dict:
        """
        Get a summary of current configuration.
        
        Returns:
            Dictionary with configuration summary
        """
        try:
            with self._lock:
                summary = {
                    'metadata': self._config_metadata.copy(),
                    'sections': {},
                    'total_preferences': 0,
                    'modified_from_defaults': 0
                }
                
                for section_name in self._config_sections.keys():
                    section_config = self._current_config.get(section_name, {})
                    default_section = self._default_config.get(section_name, {})
                    
                    modified_count = 0
                    for key, value in section_config.items():
                        if key not in default_section or default_section[key] != value:
                            modified_count += 1
                    
                    summary['sections'][section_name] = {
                        'preference_count': len(section_config),
                        'modified_from_default': modified_count
                    }
                    
                    summary['total_preferences'] += len(section_config)
                    summary['modified_from_defaults'] += modified_count
                
                return summary
                
        except Exception as e:
            log_error(f"Error generating configuration summary: {e}")
            return {}
    
    def validate_configuration(self) -> Dict[str, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Dictionary with validation errors by section
        """
        try:
            with self._lock:
                return self._validate_configuration(self._current_config, return_details=True)
        except Exception as e:
            log_error(f"Error validating configuration: {e}")
            return {'validation_error': [str(e)]}
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            os.makedirs(self.backup_dir, exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create configuration directories: {e}")
            raise
    
    def _load_configuration(self) -> None:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._current_config = data.get('configuration', {})
                self._config_metadata.update(data.get('metadata', {}))
                
                # Validate loaded configuration
                if not self._validate_configuration(self._current_config):
                    log_warning("Loaded configuration failed validation, using defaults")
                    self._current_config = self._deep_copy_config(self._default_config)
                
                log_info("Loaded library configuration")
            else:
                # Use default configuration
                self._current_config = self._deep_copy_config(self._default_config)
                self._config_metadata['created_at'] = datetime.now().isoformat()
                
                # Save default configuration
                self._save_configuration()
                
                log_info("Created default library configuration")
                
        except Exception as e:
            log_error(f"Error loading configuration: {e}")
            # Fallback to defaults
            self._current_config = self._deep_copy_config(self._default_config)
    
    def _save_configuration(self) -> bool:
        """Save configuration to file."""
        try:
            # Update metadata
            self._config_metadata['last_modified'] = datetime.now().isoformat()
            if not self._config_metadata.get('created_at'):
                self._config_metadata['created_at'] = datetime.now().isoformat()
            
            config_data = {
                'version': self._config_metadata['version'],
                'metadata': self._config_metadata,
                'configuration': self._current_config
            }
            
            # Write to temporary file first
            temp_file = self.config_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            if os.path.exists(self.config_file):
                backup_file = self.config_file + '.backup'
                os.replace(self.config_file, backup_file)
            
            os.replace(temp_file, self.config_file)
            
            # Clean up backup
            backup_file = self.config_file + '.backup'
            if os.path.exists(backup_file):
                os.remove(backup_file)
            
            return True
            
        except Exception as e:
            log_error(f"Error saving configuration: {e}")
            
            # Clean up temporary file
            temp_file = self.config_file + '.tmp'
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            return False
    
    def _create_backup(self) -> Optional[str]:
        """Create a backup of current configuration."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"config_backup_{timestamp}.json"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            success = self.export_config(backup_path)
            
            if success:
                self._config_metadata['backup_count'] = self._config_metadata.get('backup_count', 0) + 1
                log_info(f"Created configuration backup: {backup_filename}")
                return backup_path
            else:
                log_error("Failed to create configuration backup")
                return None
                
        except Exception as e:
            log_error(f"Error creating backup: {e}")
            return None
    
    def _initialize_default_config(self) -> dict:
        """Initialize default configuration."""
        return {
            'user_preferences': {
                'auto_sync': True,
                'sync_interval_hours': 24,
                'show_notifications': True,
                'confirm_installations': True,
                'auto_cleanup': True,
                'cleanup_interval_days': 30,
                'preferred_language': 'en',
                'theme': 'default'
            },
            'search_preferences': {
                'fuzzy_search': True,
                'search_suggestions': True,
                'max_suggestions': 10,
                'search_history': True,
                'max_search_history': 50,
                'default_sort': 'relevance',
                'results_per_page': 10
            },
            'display_preferences': {
                'show_trust_scores': True,
                'show_file_sizes': True,
                'show_screenshots': True,
                'compact_view': False,
                'colors_enabled': True,
                'animations_enabled': True,
                'console_width': 120
            },
            'security_preferences': {
                'min_trust_score': 5.0,
                'verify_signatures': True,
                'scan_downloads': True,
                'allow_unverified': False,
                'quarantine_suspicious': True,
                'log_security_events': True
            },
            'library_settings': {
                'cache_enabled': True,
                'cache_duration_hours': 6,
                'auto_update_tools': False,
                'parallel_downloads': 3,
                'download_timeout': 300,
                'retry_attempts': 3
            },
            'advanced_settings': {
                'debug_mode': False,
                'verbose_logging': False,
                'performance_monitoring': False,
                'analytics_enabled': True,
                'telemetry_enabled': False,
                'experimental_features': False
            }
        }
    
    def _initialize_config_schema(self) -> dict:
        """Initialize configuration validation schema."""
        return {
            'user_preferences': {
                'auto_sync': bool,
                'sync_interval_hours': int,
                'show_notifications': bool,
                'confirm_installations': bool,
                'auto_cleanup': bool,
                'cleanup_interval_days': int,
                'preferred_language': str,
                'theme': str
            },
            'search_preferences': {
                'fuzzy_search': bool,
                'search_suggestions': bool,
                'max_suggestions': int,
                'search_history': bool,
                'max_search_history': int,
                'default_sort': str,
                'results_per_page': int
            },
            'display_preferences': {
                'show_trust_scores': bool,
                'show_file_sizes': bool,
                'show_screenshots': bool,
                'compact_view': bool,
                'colors_enabled': bool,
                'animations_enabled': bool,
                'console_width': int
            },
            'security_preferences': {
                'min_trust_score': float,
                'verify_signatures': bool,
                'scan_downloads': bool,
                'allow_unverified': bool,
                'quarantine_suspicious': bool,
                'log_security_events': bool
            },
            'library_settings': {
                'cache_enabled': bool,
                'cache_duration_hours': int,
                'auto_update_tools': bool,
                'parallel_downloads': int,
                'download_timeout': int,
                'retry_attempts': int
            },
            'advanced_settings': {
                'debug_mode': bool,
                'verbose_logging': bool,
                'performance_monitoring': bool,
                'analytics_enabled': bool,
                'telemetry_enabled': bool,
                'experimental_features': bool
            }
        }
    
    def _validate_preference(self, section: str, key: str, value: Any) -> bool:
        """Validate a preference value."""
        try:
            if section not in self._config_schema:
                return False
            
            if key not in self._config_schema[section]:
                return False
            
            expected_type = self._config_schema[section][key]
            
            if not isinstance(value, expected_type):
                return False
            
            # Additional validation rules
            if key == 'min_trust_score' and not (0.0 <= value <= 10.0):
                return False
            
            if key in ['sync_interval_hours', 'cleanup_interval_days', 'max_suggestions', 
                      'max_search_history', 'results_per_page', 'cache_duration_hours',
                      'parallel_downloads', 'download_timeout', 'retry_attempts', 'console_width']:
                if value < 1:
                    return False
            
            return True
            
        except Exception as e:
            log_error(f"Error validating preference: {e}")
            return False
    
    def _validate_configuration(self, config: dict, return_details: bool = False) -> Union[bool, Dict[str, List[str]]]:
        """Validate configuration structure and values."""
        try:
            errors = {}
            
            for section_name, section_schema in self._config_schema.items():
                section_errors = []
                section_config = config.get(section_name, {})
                
                for key, expected_type in section_schema.items():
                    if key in section_config:
                        if not self._validate_preference(section_name, key, section_config[key]):
                            section_errors.append(f"Invalid value for {key}: {section_config[key]}")
                
                if section_errors:
                    errors[section_name] = section_errors
            
            if return_details:
                return errors
            else:
                return len(errors) == 0
                
        except Exception as e:
            if return_details:
                return {'validation_error': [str(e)]}
            else:
                return False
    
    def _validate_import_data(self, data: dict) -> bool:
        """Validate import data structure."""
        try:
            if not isinstance(data, dict):
                return False
            
            if 'configuration' not in data:
                return False
            
            return isinstance(data['configuration'], dict)
            
        except Exception as e:
            log_error(f"Error validating import data: {e}")
            return False
    
    def _merge_configurations(self, current: dict, imported: dict) -> dict:
        """Merge imported configuration with current configuration."""
        try:
            merged = self._deep_copy_config(current)
            
            for section_name, section_config in imported.items():
                if section_name in self._config_sections:
                    if section_name not in merged:
                        merged[section_name] = {}
                    
                    for key, value in section_config.items():
                        if self._validate_preference(section_name, key, value):
                            merged[section_name][key] = value
                        else:
                            log_warning(f"Skipped invalid imported preference: {section_name}.{key}")
            
            return merged
            
        except Exception as e:
            log_error(f"Error merging configurations: {e}")
            return current
    
    def _deep_copy_config(self, config: dict) -> dict:
        """Create a deep copy of configuration."""
        try:
            import copy
            return copy.deepcopy(config)
        except Exception as e:
            log_error(f"Error creating config copy: {e}")
            return config.copy()  # Fallback to shallow copy