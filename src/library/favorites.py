"""
Favorites Management System for Sunshine-AIO Community Library

This module provides user preferences and favorites management with import/export
functionality and intelligent recommendations based on user behavior.
"""

import os
import json
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from misc.Logger import log_info, log_error, log_warning, log_success
from .tool_provider import ToolInfo


class FavoritesManager:
    """
    User favorites and preferences management with recommendation engine
    and data persistence capabilities.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize the favorites manager.
        
        Args:
            base_path: Base path for storing user data
        """
        self.base_path = base_path
        self.favorites_dir = os.path.join(base_path, "user_data", "library")
        self.favorites_file = os.path.join(self.favorites_dir, "favorites.json")
        self.preferences_file = os.path.join(self.favorites_dir, "preferences.json")
        self.activity_file = os.path.join(self.favorites_dir, "activity.json")
        
        # In-memory storage
        self._favorites: Set[str] = set()
        self._preferences: Dict[str, Any] = {}
        self._activity_log: List[Dict[str, Any]] = []
        
        # Default preferences
        self._default_preferences = {
            'auto_recommendations': True,
            'recommendation_count': 5,
            'activity_tracking': True,
            'show_installation_hints': True,
            'preferred_categories': [],
            'preferred_platforms': ['windows'],
            'min_trust_score': 5.0,
            'max_tool_size': '100MB',
            'exclude_tags': [],
            'notification_settings': {
                'new_tools': True,
                'tool_updates': True,
                'recommendations': True
            }
        }
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing data
        self._load_data()
        
        log_info("FavoritesManager initialized")
    
    def add_favorite(self, tool_id: str) -> bool:
        """
        Add a tool to favorites.
        
        Args:
            tool_id: ID of the tool to add to favorites
            
        Returns:
            True if successfully added, False if already exists or error
        """
        try:
            if not tool_id or not tool_id.strip():
                log_warning("Invalid tool ID provided for favorites")
                return False
            
            tool_id = tool_id.strip()
            
            if tool_id in self._favorites:
                log_info(f"Tool {tool_id} already in favorites")
                return False
            
            self._favorites.add(tool_id)
            self._log_activity('favorite_added', tool_id)
            
            # Save to file
            success = self._save_favorites()
            
            if success:
                log_success(f"Added {tool_id} to favorites")
            else:
                # Rollback on save failure
                self._favorites.discard(tool_id)
                log_error(f"Failed to save favorites after adding {tool_id}")
            
            return success
            
        except Exception as e:
            log_error(f"Error adding favorite {tool_id}: {e}")
            return False
    
    def remove_favorite(self, tool_id: str) -> bool:
        """
        Remove a tool from favorites.
        
        Args:
            tool_id: ID of the tool to remove from favorites
            
        Returns:
            True if successfully removed, False if not in favorites or error
        """
        try:
            if not tool_id or not tool_id.strip():
                log_warning("Invalid tool ID provided for favorites removal")
                return False
            
            tool_id = tool_id.strip()
            
            if tool_id not in self._favorites:
                log_info(f"Tool {tool_id} not in favorites")
                return False
            
            self._favorites.discard(tool_id)
            self._log_activity('favorite_removed', tool_id)
            
            # Save to file
            success = self._save_favorites()
            
            if success:
                log_success(f"Removed {tool_id} from favorites")
            else:
                # Rollback on save failure
                self._favorites.add(tool_id)
                log_error(f"Failed to save favorites after removing {tool_id}")
            
            return success
            
        except Exception as e:
            log_error(f"Error removing favorite {tool_id}: {e}")
            return False
    
    def is_favorite(self, tool_id: str) -> bool:
        """
        Check if a tool is in favorites.
        
        Args:
            tool_id: ID of the tool to check
            
        Returns:
            True if tool is in favorites
        """
        try:
            if not tool_id:
                return False
            
            return tool_id.strip() in self._favorites
            
        except Exception as e:
            log_error(f"Error checking favorite status for {tool_id}: {e}")
            return False
    
    def get_favorites(self) -> List[str]:
        """
        Get list of all favorite tool IDs.
        
        Returns:
            List of favorite tool IDs
        """
        try:
            return sorted(list(self._favorites))
        except Exception as e:
            log_error(f"Error getting favorites list: {e}")
            return []
    
    def get_favorite_tools(self, library_manager) -> List[ToolInfo]:
        """
        Get ToolInfo objects for all favorite tools.
        
        Args:
            library_manager: LibraryManager instance to fetch tool data
            
        Returns:
            List of ToolInfo objects for favorite tools
        """
        try:
            favorite_tools = []
            tools_dict = library_manager.get_available_tools()
            
            for tool_id in self._favorites:
                if tool_id in tools_dict:
                    tool_data = tools_dict[tool_id]
                    tool_info = self._dict_to_tool_info(tool_data, tool_id)
                    favorite_tools.append(tool_info)
                else:
                    log_warning(f"Favorite tool not found in library: {tool_id}")
            
            # Sort by name
            favorite_tools.sort(key=lambda x: x.name.lower())
            
            log_info(f"Retrieved {len(favorite_tools)} favorite tools")
            return favorite_tools
            
        except Exception as e:
            log_error(f"Error getting favorite tools: {e}")
            return []
    
    def export_favorites(self, file_path: str) -> bool:
        """
        Export favorites to a file.
        
        Args:
            file_path: Path to export file
            
        Returns:
            True if export was successful
        """
        try:
            export_data = {
                'version': '1.0',
                'export_date': datetime.now().isoformat(),
                'favorites': list(self._favorites),
                'preferences': self._preferences,
                'activity_summary': self._get_activity_summary()
            }
            
            # Ensure export directory exists
            export_dir = os.path.dirname(file_path)
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            log_success(f"Exported favorites to {file_path}")
            return True
            
        except Exception as e:
            log_error(f"Error exporting favorites: {e}")
            return False
    
    def import_favorites(self, file_path: str) -> bool:
        """
        Import favorites from a file.
        
        Args:
            file_path: Path to import file
            
        Returns:
            True if import was successful
        """
        try:
            if not os.path.exists(file_path):
                log_error(f"Import file not found: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if not isinstance(import_data, dict) or 'favorites' not in import_data:
                log_error("Invalid import file format")
                return False
            
            # Backup current data
            backup_favorites = self._favorites.copy()
            backup_preferences = self._preferences.copy()
            
            try:
                # Import favorites
                imported_favorites = import_data.get('favorites', [])
                if isinstance(imported_favorites, list):
                    for tool_id in imported_favorites:
                        if isinstance(tool_id, str) and tool_id.strip():
                            self._favorites.add(tool_id.strip())
                
                # Import preferences (merge with existing)
                imported_preferences = import_data.get('preferences', {})
                if isinstance(imported_preferences, dict):
                    self._preferences.update(imported_preferences)
                
                # Save imported data
                self._save_favorites()
                self._save_preferences()
                
                self._log_activity('favorites_imported', f"from_{os.path.basename(file_path)}")
                
                log_success(f"Imported favorites from {file_path}")
                return True
                
            except Exception as save_error:
                # Restore backup on error
                self._favorites = backup_favorites
                self._preferences = backup_preferences
                log_error(f"Error saving imported data, restored backup: {save_error}")
                return False
            
        except Exception as e:
            log_error(f"Error importing favorites: {e}")
            return False
    
    def get_recommendations(self, library_manager, count: int = None) -> List[ToolInfo]:
        """
        Get tool recommendations based on user preferences and activity.
        
        Args:
            library_manager: LibraryManager instance to fetch tool data
            count: Number of recommendations to return (uses preference if None)
            
        Returns:
            List of recommended ToolInfo objects
        """
        try:
            if not self._preferences.get('auto_recommendations', True):
                log_info("Auto recommendations disabled")
                return []
            
            if count is None:
                count = self._preferences.get('recommendation_count', 5)
            
            tools_dict = library_manager.get_available_tools()
            if not tools_dict:
                log_warning("No tools available for recommendations")
                return []
            
            # Get all tools except favorites
            candidate_tools = []
            for tool_id, tool_data in tools_dict.items():
                if tool_id not in self._favorites:
                    tool_info = self._dict_to_tool_info(tool_data, tool_id)
                    candidate_tools.append(tool_info)
            
            if not candidate_tools:
                log_info("No candidate tools for recommendations")
                return []
            
            # Score tools based on user preferences and activity
            scored_tools = []
            for tool in candidate_tools:
                score = self._calculate_recommendation_score(tool)
                if score > 0:
                    scored_tools.append((tool, score))
            
            # Sort by score and return top results
            scored_tools.sort(key=lambda x: x[1], reverse=True)
            recommendations = [tool for tool, _ in scored_tools[:count]]
            
            log_info(f"Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            log_error(f"Error getting recommendations: {e}")
            return []
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """
        Get user preferences.
        
        Returns:
            Dictionary of user preferences
        """
        try:
            return self._preferences.copy()
        except Exception as e:
            log_error(f"Error getting user preferences: {e}")
            return self._default_preferences.copy()
    
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
            if not key or not key.strip():
                log_warning("Invalid preference key")
                return False
            
            old_value = self._preferences.get(key)
            self._preferences[key] = value
            
            # Save preferences
            success = self._save_preferences()
            
            if success:
                self._log_activity('preference_changed', f"{key}:{old_value}->{value}")
                log_info(f"Updated preference {key}")
            else:
                # Rollback on save failure
                if old_value is not None:
                    self._preferences[key] = old_value
                else:
                    self._preferences.pop(key, None)
                log_error(f"Failed to save preference {key}")
            
            return success
            
        except Exception as e:
            log_error(f"Error setting preference {key}: {e}")
            return False
    
    def reset_preferences(self) -> bool:
        """
        Reset preferences to defaults.
        
        Returns:
            True if reset was successful
        """
        try:
            backup_preferences = self._preferences.copy()
            self._preferences = self._default_preferences.copy()
            
            success = self._save_preferences()
            
            if success:
                self._log_activity('preferences_reset', 'all')
                log_success("Reset preferences to defaults")
            else:
                # Restore backup on save failure
                self._preferences = backup_preferences
                log_error("Failed to save reset preferences")
            
            return success
            
        except Exception as e:
            log_error(f"Error resetting preferences: {e}")
            return False
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """
        Get user activity summary.
        
        Returns:
            Dictionary with activity statistics
        """
        try:
            return self._get_activity_summary()
        except Exception as e:
            log_error(f"Error getting activity summary: {e}")
            return {}
    
    def clear_activity_log(self, days_to_keep: int = 30) -> bool:
        """
        Clear old activity log entries.
        
        Args:
            days_to_keep: Number of days of activity to keep
            
        Returns:
            True if cleanup was successful
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            original_count = len(self._activity_log)
            self._activity_log = [
                entry for entry in self._activity_log
                if self._parse_activity_date(entry.get('timestamp', '')) >= cutoff_date
            ]
            
            removed_count = original_count - len(self._activity_log)
            
            # Save cleaned activity log
            success = self._save_activity()
            
            if success:
                log_info(f"Cleaned activity log: removed {removed_count} old entries")
            else:
                log_error("Failed to save cleaned activity log")
            
            return success
            
        except Exception as e:
            log_error(f"Error clearing activity log: {e}")
            return False
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            os.makedirs(self.favorites_dir, exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create favorites directory: {e}")
            raise
    
    def _load_data(self) -> None:
        """Load favorites, preferences, and activity from files."""
        try:
            # Load favorites
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    favorites_data = json.load(f)
                    if isinstance(favorites_data, list):
                        self._favorites = set(favorites_data)
                    elif isinstance(favorites_data, dict):
                        self._favorites = set(favorites_data.get('favorites', []))
                
                log_info(f"Loaded {len(self._favorites)} favorites")
            
            # Load preferences
            if os.path.exists(self.preferences_file):
                with open(self.preferences_file, 'r', encoding='utf-8') as f:
                    preferences_data = json.load(f)
                    if isinstance(preferences_data, dict):
                        # Merge with defaults
                        self._preferences = self._default_preferences.copy()
                        self._preferences.update(preferences_data)
                
                log_info("Loaded user preferences")
            else:
                self._preferences = self._default_preferences.copy()
            
            # Load activity log
            if os.path.exists(self.activity_file):
                with open(self.activity_file, 'r', encoding='utf-8') as f:
                    activity_data = json.load(f)
                    if isinstance(activity_data, list):
                        self._activity_log = activity_data
                
                log_info(f"Loaded {len(self._activity_log)} activity entries")
            
        except Exception as e:
            log_error(f"Error loading user data: {e}")
            # Initialize with defaults on error
            self._favorites = set()
            self._preferences = self._default_preferences.copy()
            self._activity_log = []
    
    def _save_favorites(self) -> bool:
        """Save favorites to file."""
        try:
            favorites_data = {
                'version': '1.0',
                'updated': datetime.now().isoformat(),
                'favorites': list(self._favorites)
            }
            
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(favorites_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            log_error(f"Error saving favorites: {e}")
            return False
    
    def _save_preferences(self) -> bool:
        """Save preferences to file."""
        try:
            preferences_data = self._preferences.copy()
            preferences_data['last_updated'] = datetime.now().isoformat()
            
            with open(self.preferences_file, 'w', encoding='utf-8') as f:
                json.dump(preferences_data, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            log_error(f"Error saving preferences: {e}")
            return False
    
    def _save_activity(self) -> bool:
        """Save activity log to file."""
        try:
            with open(self.activity_file, 'w', encoding='utf-8') as f:
                json.dump(self._activity_log, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            log_error(f"Error saving activity log: {e}")
            return False
    
    def _log_activity(self, action: str, details: str) -> None:
        """Log user activity."""
        try:
            if not self._preferences.get('activity_tracking', True):
                return
            
            activity_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': action,
                'details': details
            }
            
            self._activity_log.append(activity_entry)
            
            # Limit activity log size
            max_entries = 1000
            if len(self._activity_log) > max_entries:
                self._activity_log = self._activity_log[-max_entries:]
            
            # Save activity log periodically
            if len(self._activity_log) % 10 == 0:
                self._save_activity()
            
        except Exception as e:
            log_error(f"Error logging activity: {e}")
    
    def _get_activity_summary(self) -> Dict[str, Any]:
        """Get activity summary statistics."""
        try:
            summary = {
                'total_entries': len(self._activity_log),
                'actions': defaultdict(int),
                'recent_activity': [],
                'favorite_trends': {
                    'added_last_week': 0,
                    'removed_last_week': 0
                }
            }
            
            # Count actions
            for entry in self._activity_log:
                action = entry.get('action', 'unknown')
                summary['actions'][action] += 1
            
            # Recent activity (last 10 entries)
            summary['recent_activity'] = self._activity_log[-10:]
            
            # Favorite trends
            last_week = datetime.now() - timedelta(days=7)
            for entry in self._activity_log:
                entry_date = self._parse_activity_date(entry.get('timestamp', ''))
                if entry_date >= last_week:
                    action = entry.get('action', '')
                    if action == 'favorite_added':
                        summary['favorite_trends']['added_last_week'] += 1
                    elif action == 'favorite_removed':
                        summary['favorite_trends']['removed_last_week'] += 1
            
            return dict(summary)
            
        except Exception as e:
            log_error(f"Error generating activity summary: {e}")
            return {}
    
    def _calculate_recommendation_score(self, tool: ToolInfo) -> float:
        """Calculate recommendation score for a tool."""
        try:
            score = 0.0
            
            # Base score from tool quality
            trust_score = getattr(tool, 'trust_score', 5.0)
            score += min(trust_score / 10.0, 1.0) * 2.0  # Max 2.0 points
            
            # Category preference
            preferred_categories = self._preferences.get('preferred_categories', [])
            tool_category = getattr(tool, 'category', '')
            if tool_category in preferred_categories:
                score += 3.0
            
            # Platform compatibility
            preferred_platforms = self._preferences.get('preferred_platforms', ['windows'])
            tool_platforms = getattr(tool, 'platforms', ['windows'])
            if isinstance(tool_platforms, str):
                tool_platforms = [tool_platforms]
            
            if any(platform in tool_platforms for platform in preferred_platforms):
                score += 2.0
            
            # Size preference
            max_size_str = self._preferences.get('max_tool_size', '100MB')
            tool_size = getattr(tool, 'size', 0)
            
            try:
                max_size = self._parse_size_preference(max_size_str)
                if tool_size <= max_size:
                    score += 1.0
                else:
                    score -= 1.0  # Penalty for oversized tools
            except:
                pass
            
            # Tag preferences (avoid excluded tags)
            excluded_tags = self._preferences.get('exclude_tags', [])
            tool_tags = getattr(tool, 'tags', [])
            if isinstance(tool_tags, str):
                tool_tags = [tool_tags]
            
            if any(tag in excluded_tags for tag in tool_tags):
                score -= 2.0
            
            # Activity-based scoring
            # Tools in similar categories to favorites get bonus
            favorite_categories = self._get_favorite_categories()
            if tool_category in favorite_categories:
                score += 1.0
            
            return max(score, 0.0)  # Ensure non-negative score
            
        except Exception as e:
            log_error(f"Error calculating recommendation score: {e}")
            return 0.0
    
    def _get_favorite_categories(self) -> List[str]:
        """Get categories of favorite tools."""
        try:
            # This would need library_manager access in a real implementation
            # For now, return empty list
            return []
        except Exception as e:
            log_error(f"Error getting favorite categories: {e}")
            return []
    
    def _parse_size_preference(self, size_str: str) -> int:
        """Parse size preference string to bytes."""
        try:
            size_str = size_str.strip().lower()
            
            # Extract number and unit
            import re
            match = re.match(r'(\d+(?:\.\d+)?)\s*([a-z]*)', size_str)
            if match:
                number, unit = match.groups()
                number = float(number)
                
                units = {
                    'b': 1,
                    'kb': 1024,
                    'mb': 1024 * 1024,
                    'gb': 1024 * 1024 * 1024
                }
                
                multiplier = units.get(unit or 'b', 1)
                return int(number * multiplier)
            
            return 0
            
        except Exception as e:
            log_error(f"Error parsing size preference: {e}")
            return 100 * 1024 * 1024  # Default to 100MB
    
    def _parse_activity_date(self, timestamp_str: str) -> datetime:
        """Parse activity timestamp string."""
        try:
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.min
        except Exception as e:
            log_error(f"Error parsing activity date: {e}")
            return datetime.min
    
    def _dict_to_tool_info(self, tool_data: Dict[str, Any], tool_id: str) -> ToolInfo:
        """Convert tool dictionary to ToolInfo object."""
        try:
            if hasattr(ToolInfo, 'from_dict'):
                return ToolInfo.from_dict(tool_data)
            else:
                # Manual creation as fallback
                return ToolInfo(
                    id=tool_id,
                    name=tool_data.get('name', tool_id),
                    description=tool_data.get('description', ''),
                    category=tool_data.get('category', 'General'),
                    version=tool_data.get('version', '1.0.0'),
                    author=tool_data.get('author', 'Unknown'),
                    download_url=tool_data.get('download_url', ''),
                    size=tool_data.get('size', 0),
                    trust_score=tool_data.get('trust_score', 5.0),
                    platforms=tool_data.get('platforms', ['windows']),
                    tags=tool_data.get('tags', [])
                )
        except Exception as e:
            log_error(f"Error creating ToolInfo for {tool_id}: {e}")
            return ToolInfo(
                id=tool_id,
                name=tool_data.get('name', tool_id),
                description=tool_data.get('description', ''),
                category='General',
                version='1.0.0',
                author='Unknown'
            )