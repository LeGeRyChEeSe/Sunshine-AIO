"""
Library Manager for Sunshine-AIO Community Library Integration

This module provides the main LibraryManager class that coordinates all library operations
including fetching available tools, managing cache, and handling tool metadata.
"""

import os
import json
import threading
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import requests

from misc.Logger import log_info, log_error, log_warning, log_success, log_progress


class LibraryManager:
    """
    Main library management class for coordinating library operations.
    
    This class handles:
    - Fetching available tools from the community repository
    - Managing local cache of tool metadata
    - Coordinating with other library components
    - Error handling and fallback mechanisms
    """
    
    def __init__(self, base_path: str, repository_url: str = None, cache_dir: str = None):
        """
        Initialize the LibraryManager.
        
        Args:
            base_path: Base path of the Sunshine-AIO application
            repository_url: URL of the community library repository
            cache_dir: Directory for storing cached metadata
        """
        self.base_path = base_path
        self.repository_url = repository_url or "https://github.com/LeGeRyChEeSe/sunshine-aio-library"
        self.cache_dir = cache_dir or os.path.join(base_path, "cache", "library")
        
        # Configuration defaults
        self.config = {
            'sync_interval': 3600,  # 1 hour in seconds
            'validation_enabled': True,
            'max_retries': 3,
            'timeout': 30,
            'user_agent': 'Sunshine-AIO/1.0'
        }
        
        # Internal state
        self._tools_cache: Dict[str, Any] = {}
        self._last_sync: Optional[datetime] = None
        self._sync_lock = threading.Lock()
        self._initialized = False
        
        # Ensure cache directory exists
        self._ensure_cache_directory()
        
        log_info(f"LibraryManager initialized with repository: {self.repository_url}")
    
    def _ensure_cache_directory(self) -> None:
        """Ensure the cache directory exists."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            log_info(f"Cache directory ensured: {self.cache_dir}")
        except OSError as e:
            log_error(f"Failed to create cache directory {self.cache_dir}: {e}")
            raise
    
    def initialize(self) -> bool:
        """
        Initialize the library manager and perform initial sync if needed.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            log_info("Initializing LibraryManager...")
            
            # Load cached metadata if available
            self._load_cached_metadata()
            
            # Check if we need to sync
            if self._should_sync():
                log_info("Performing initial library sync...")
                success = self.sync_library_metadata()
                if not success:
                    log_warning("Initial sync failed, using cached data if available")
            
            self._initialized = True
            log_success("LibraryManager initialized successfully")
            return True
            
        except Exception as e:
            log_error(f"Failed to initialize LibraryManager: {e}")
            return False
    
    def _should_sync(self) -> bool:
        """
        Check if we should perform a library sync.
        
        Returns:
            bool: True if sync is needed
        """
        if not self._last_sync:
            return True
        
        time_since_sync = datetime.now() - self._last_sync
        return time_since_sync.total_seconds() > self.config['sync_interval']
    
    def sync_library_metadata(self) -> bool:
        """
        Synchronize library metadata from the remote repository.
        
        Returns:
            bool: True if sync was successful
        """
        with self._sync_lock:
            try:
                log_info("Starting library metadata sync...")
                
                # Fetch metadata from repository
                metadata = self._fetch_repository_metadata()
                if not metadata:
                    log_error("Failed to fetch repository metadata")
                    return False
                
                # Update cache
                self._update_cache(metadata)
                
                # Update last sync time
                self._last_sync = datetime.now()
                
                log_success(f"Library metadata sync completed. Found {len(metadata.get('tools', {}))} tools")
                return True
                
            except Exception as e:
                log_error(f"Library sync failed: {e}")
                return False
    
    def _fetch_repository_metadata(self) -> Optional[Dict[str, Any]]:
        """
        Fetch metadata from the remote repository using the static API.
        
        Returns:
            Dict containing repository metadata or None on failure
        """
        try:
            # Use the static API endpoint instead of GitHub contents API
            api_url = self._get_catalog_api_url()
            
            headers = {
                'User-Agent': self.config['user_agent'],
                'Accept': 'application/json'
            }
            
            log_info(f"Fetching tools catalog from: {api_url}")
            
            response = requests.get(
                api_url,
                headers=headers,
                timeout=self.config['timeout']
            )
            
            response.raise_for_status()
            
            # Parse the catalog response directly
            catalog_data = response.json()
            metadata = self._parse_catalog_data(catalog_data)
            
            return metadata
            
        except requests.RequestException as e:
            log_error(f"Network error fetching repository metadata: {e}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            log_error(f"Unexpected error fetching metadata: {e}")
            return None
    
    def _get_catalog_api_url(self) -> str:
        """
        Get the catalog API URL for the static JSON API.
        
        Returns:
            str: URL for the catalog.json API endpoint
        """
        # Extract owner and repo from GitHub URL
        if "github.com/" in self.repository_url:
            parts = self.repository_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                return f"https://raw.githubusercontent.com/{owner}/{repo}/main/api/catalog.json"
        
        # Fallback - assume it's already an API URL
        return f"{self.repository_url}/raw/main/api/catalog.json"
    
    def _parse_catalog_data(self, catalog_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse catalog data from the static API and build metadata structure.
        
        Args:
            catalog_data: Catalog data from the static API
            
        Returns:
            Dict containing parsed metadata
        """
        try:
            # The catalog already contains the right structure, we just need to adapt it
            tools = {}
            categories = {}
            
            # Process tools from the catalog
            for tool_data in catalog_data.get('tools', []):
                tool_id = tool_data.get('name', tool_data.get('id', 'unknown'))
                
                # Convert catalog tool format to our internal format
                tools[tool_id] = {
                    'id': tool_id,
                    'name': tool_data.get('name', tool_id),
                    'description': tool_data.get('description', ''),
                    'version': tool_data.get('version', '1.0.0'),
                    'category': tool_data.get('category', 'General'),
                    'tags': tool_data.get('tags', []),
                    'author': tool_data.get('maintainer', {}).get('name', 'Unknown'),
                    'repository': tool_data.get('repository', ''),
                    'documentation': tool_data.get('documentation', ''),
                    'license': tool_data.get('license', 'Unknown'),
                    'platforms': tool_data.get('platforms', []),
                    'language': tool_data.get('language', 'Unknown'),
                    'added_date': tool_data.get('added_date', datetime.now().isoformat()),
                    'contributed_by': tool_data.get('contributed_by', 'Community'),
                    'validated': tool_data.get('status') == 'verified',
                    'quality_score': tool_data.get('quality_score', 0),
                    'github_stars': tool_data.get('github_stars', 0),
                    'github_forks': tool_data.get('github_forks', 0),
                    'last_activity': tool_data.get('last_activity', ''),
                    'verification_status': tool_data.get('status', 'pending')
                }
                
                # Track categories
                category = tool_data.get('category', 'General')
                if category not in categories:
                    categories[category] = {
                        'name': category,
                        'tools': []
                    }
                categories[category]['tools'].append(tool_id)
            
            metadata = {
                'last_updated': catalog_data.get('generated_at', datetime.now().isoformat()),
                'tools': tools,
                'categories': categories,
                'repository_info': {
                    'url': self.repository_url,
                    'total_tools': len(tools),
                    'catalog_version': catalog_data.get('version', '1.0.0'),
                    'api_version': catalog_data.get('api_version', '1.0')
                }
            }
            
            log_info(f"Parsed catalog data: {len(tools)} tools found across {len(categories)} categories")
            return metadata
            
        except Exception as e:
            log_error(f"Error parsing catalog data: {e}")
            # Return empty structure on error
            return {
                'last_updated': datetime.now().isoformat(),
                'tools': {},
                'categories': {},
                'repository_info': {
                    'url': self.repository_url,
                    'total_tools': 0
                }
            }
    
    def _update_cache(self, metadata: Dict[str, Any]) -> None:
        """
        Update local cache with new metadata.
        
        Args:
            metadata: Metadata dictionary to cache
        """
        try:
            cache_file = os.path.join(self.cache_dir, "tools_metadata.json")
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Update in-memory cache
            self._tools_cache = metadata.copy()
            
            log_info(f"Cache updated: {cache_file}")
            
        except Exception as e:
            log_error(f"Failed to update cache: {e}")
            raise
    
    def _load_cached_metadata(self) -> None:
        """Load metadata from cache if available."""
        try:
            cache_file = os.path.join(self.cache_dir, "tools_metadata.json")
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._tools_cache = json.load(f)
                
                # Parse last updated time
                if 'last_updated' in self._tools_cache:
                    self._last_sync = datetime.fromisoformat(
                        self._tools_cache['last_updated']
                    )
                
                log_info(f"Loaded cached metadata: {len(self._tools_cache.get('tools', {}))} tools")
            else:
                log_info("No cached metadata found")
                
        except Exception as e:
            log_warning(f"Failed to load cached metadata: {e}")
            self._tools_cache = {}
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available tools from the library.
        
        Returns:
            Dict mapping tool IDs to tool metadata
        """
        if not self._initialized:
            log_warning("LibraryManager not initialized, attempting initialization...")
            if not self.initialize():
                log_error("Failed to initialize LibraryManager")
                return {}
        
        return self._tools_cache.get('tools', {})
    
    def get_tool_info(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_id: ID of the tool to get info for
            
        Returns:
            Dict containing tool information or None if not found
        """
        tools = self.get_available_tools()
        return tools.get(tool_id)
    
    def search_tools(self, query: str, category: str = None) -> Dict[str, Dict[str, Any]]:
        """
        Search for tools matching a query.
        
        Args:
            query: Search query string
            category: Optional category filter
            
        Returns:
            Dict of matching tools
        """
        tools = self.get_available_tools()
        results = {}
        
        query_lower = query.lower()
        
        for tool_id, tool_info in tools.items():
            # Check if tool matches query
            matches_query = (
                query_lower in tool_id.lower() or
                query_lower in tool_info.get('name', '').lower() or
                query_lower in tool_info.get('description', '').lower()
            )
            
            # Check category filter
            matches_category = (
                category is None or
                tool_info.get('category', '').lower() == category.lower()
            )
            
            if matches_query and matches_category:
                results[tool_id] = tool_info
        
        log_info(f"Search for '{query}' returned {len(results)} results")
        return results
    
    def get_categories(self) -> List[str]:
        """
        Get all available tool categories.
        
        Returns:
            List of category names
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        # Use categories from metadata if available
        categories_data = self._tools_cache.get('categories', {})
        if categories_data:
            return sorted(list(categories_data.keys()))
        
        # Fallback: extract categories from tools
        tools = self.get_available_tools()
        categories = set()
        
        for tool_info in tools.values():
            category = tool_info.get('category', 'General')
            categories.add(category)
        
        return sorted(list(categories))
    
    def get_tools_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Category name to filter by
            
        Returns:
            Dict of tools in the category
        """
        tools = self.get_available_tools()
        return {
            tool_id: tool_info 
            for tool_id, tool_info in tools.items()
            if tool_info.get('category', 'General') == category
        }
    
    def get_tools_sorted_by_quality(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get tools sorted by quality score (highest first).
        
        Args:
            limit: Maximum number of tools to return
            
        Returns:
            List of tools sorted by quality score
        """
        tools = self.get_available_tools()
        
        # Convert to list and sort by quality score
        tools_list = list(tools.values())
        tools_list.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        if limit:
            tools_list = tools_list[:limit]
            
        return tools_list
    
    def get_verified_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get only verified/validated tools.
        
        Returns:
            Dict of verified tools
        """
        tools = self.get_available_tools()
        return {
            tool_id: tool_info 
            for tool_id, tool_info in tools.items()
            if tool_info.get('validated', False) or tool_info.get('verification_status') == 'verified'
        }
    
    def is_tool_available(self, tool_id: str) -> bool:
        """
        Check if a tool is available in the library.
        
        Args:
            tool_id: ID of the tool to check
            
        Returns:
            bool: True if tool is available
        """
        return tool_id in self.get_available_tools()
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current synchronization status.
        
        Returns:
            Dict containing sync status information
        """
        return {
            'initialized': self._initialized,
            'last_sync': self._last_sync.isoformat() if self._last_sync else None,
            'cache_dir': self.cache_dir,
            'repository_url': self.repository_url,
            'total_tools': len(self._tools_cache.get('tools', {})),
            'sync_needed': self._should_sync()
        }
    
    def force_sync(self) -> bool:
        """
        Force a synchronization regardless of timing.
        
        Returns:
            bool: True if sync was successful
        """
        log_info("Forcing library synchronization...")
        return self.sync_library_metadata()
    
    def clear_cache(self) -> bool:
        """
        Clear the local cache.
        
        Returns:
            bool: True if cache was cleared successfully
        """
        try:
            cache_file = os.path.join(self.cache_dir, "tools_metadata.json")
            
            if os.path.exists(cache_file):
                os.remove(cache_file)
            
            self._tools_cache = {}
            self._last_sync = None
            
            log_success("Library cache cleared")
            return True
            
        except Exception as e:
            log_error(f"Failed to clear cache: {e}")
            return False


    def download_and_install_tool(self, tool_id: str, **kwargs) -> bool:
        """
        Download and install a tool from the library.
        
        Args:
            tool_id: ID of the tool to download and install
            **kwargs: Additional installation parameters
            
        Returns:
            True if download and installation were successful
        """
        try:
            log_info(f"Starting download and installation for tool: {tool_id}")
            
            # Get tool information
            tool_info = self.get_tool_info(tool_id)
            if not tool_info:
                log_error(f"Tool not found in library: {tool_id}")
                return False
            
            # Import required components
            from .downloader import LibraryDownloader
            from .installer import HybridInstaller
            from .tool_provider import ToolInfo
            from misc.SystemRequests import SystemRequests
            from misc.Config import DownloadManager
            
            # Convert dict to ToolInfo if needed
            if isinstance(tool_info, dict):
                tool_info_obj = ToolInfo.from_dict(tool_info)
            else:
                tool_info_obj = tool_info
            
            # Initialize components
            cache_dir = os.path.join(self.base_path, "cache", "downloads")
            downloader = LibraryDownloader(cache_dir)
            
            # Create system requests and download manager for installer
            system_requests = SystemRequests(self.base_path)
            download_manager = DownloadManager(system_requests, 0)
            installer = HybridInstaller(system_requests, download_manager)
            
            # Download tool files
            log_progress("Downloading tool files...")
            downloaded_file = downloader.download_tool_files(tool_info_obj)
            if not downloaded_file:
                log_error(f"Failed to download tool: {tool_id}")
                return False
            
            # Install tool
            log_progress("Installing tool...")
            result = installer.install_library_tool(tool_info_obj)
            
            if result and result.success:
                log_success(f"Successfully downloaded and installed tool: {tool_id}")
                return True
            else:
                error_msg = result.error_message if result else "Unknown installation error"
                log_error(f"Installation failed for {tool_id}: {error_msg}")
                return False
                
        except Exception as e:
            log_error(f"Error downloading and installing tool {tool_id}: {e}")
            return False
    
    def get_tool_installation_status(self, tool_id: str) -> Dict[str, Any]:
        """
        Get the installation status of a tool.
        
        Args:
            tool_id: ID of the tool
            
        Returns:
            Dict containing installation status information
        """
        try:
            from .installer import HybridInstaller
            from misc.SystemRequests import SystemRequests
            from misc.Config import DownloadManager
            
            # Initialize installer to check status
            system_requests = SystemRequests(self.base_path)
            download_manager = DownloadManager(system_requests, 0)
            installer = HybridInstaller(system_requests, download_manager)
            
            return installer.get_installation_status(tool_id)
            
        except Exception as e:
            log_error(f"Error getting installation status for {tool_id}: {e}")
            return {
                'tool_id': tool_id,
                'status': 'error',
                'error': str(e)
            }
    
    def uninstall_tool(self, tool_id: str) -> bool:
        """
        Uninstall a tool.
        
        Args:
            tool_id: ID of the tool to uninstall
            
        Returns:
            True if uninstallation was successful
        """
        try:
            log_info(f"Starting uninstallation for tool: {tool_id}")
            
            from .installer import HybridInstaller
            from misc.SystemRequests import SystemRequests
            from misc.Config import DownloadManager
            
            # Initialize installer
            system_requests = SystemRequests(self.base_path)
            download_manager = DownloadManager(system_requests, 0)
            installer = HybridInstaller(system_requests, download_manager)
            
            # Perform uninstallation
            success = installer.uninstall_tool(tool_id)
            
            if success:
                log_success(f"Successfully uninstalled tool: {tool_id}")
            else:
                log_error(f"Failed to uninstall tool: {tool_id}")
            
            return success
            
        except Exception as e:
            log_error(f"Error uninstalling tool {tool_id}: {e}")
            return False
    
    def update_tool_metadata(self, tool_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Update metadata for a specific tool.
        
        Args:
            tool_id: ID of the tool
            metadata: Updated metadata dictionary
            
        Returns:
            True if update was successful
        """
        try:
            if tool_id in self._tools_cache.get('tools', {}):
                self._tools_cache['tools'][tool_id].update(metadata)
                
                # Save updated cache
                cache_file = os.path.join(self.cache_dir, "tools_metadata.json")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self._tools_cache, f, indent=2, ensure_ascii=False)
                
                log_info(f"Updated metadata for tool: {tool_id}")
                return True
            else:
                log_warning(f"Tool not found for metadata update: {tool_id}")
                return False
                
        except Exception as e:
            log_error(f"Error updating tool metadata: {e}")
            return False
    
    def get_download_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the download cache.
        
        Returns:
            Dict containing cache information
        """
        try:
            from .downloader import LibraryDownloader
            
            cache_dir = os.path.join(self.base_path, "cache", "downloads")
            downloader = LibraryDownloader(cache_dir)
            
            return downloader.get_cache_info()
            
        except Exception as e:
            log_error(f"Error getting download cache info: {e}")
            return {'error': str(e)}
    
    def clear_download_cache(self, tool_id: str = None) -> bool:
        """
        Clear download cache for specific tool or all tools.
        
        Args:
            tool_id: Specific tool ID to clear (None for all)
            
        Returns:
            True if cache was cleared successfully
        """
        try:
            from .downloader import LibraryDownloader
            
            cache_dir = os.path.join(self.base_path, "cache", "downloads")
            downloader = LibraryDownloader(cache_dir)
            
            success = downloader.clear_cache(tool_id)
            
            if success:
                if tool_id:
                    log_success(f"Cleared download cache for tool: {tool_id}")
                else:
                    log_success("Cleared all download cache")
            else:
                log_error("Failed to clear download cache")
            
            return success
            
        except Exception as e:
            log_error(f"Error clearing download cache: {e}")
            return False
    
    def validate_tool_integrity(self, tool_id: str) -> bool:
        """
        Validate the integrity of an installed tool.
        
        Args:
            tool_id: ID of the tool to validate
            
        Returns:
            True if tool integrity is valid
        """
        try:
            from .validators import ToolValidator
            
            # Get tool info
            tool_info = self.get_tool_info(tool_id)
            if not tool_info:
                log_error(f"Tool not found for validation: {tool_id}")
                return False
            
            # Initialize validator and check integrity
            validator = ToolValidator()
            
            # Check if tool is installed
            tools_dir = os.path.join(self.base_path, "tools", tool_id)
            if not os.path.exists(tools_dir):
                log_warning(f"Tool directory not found: {tools_dir}")
                return False
            
            # Basic validation - check for expected files
            has_files = any(os.path.isfile(os.path.join(root, file)) 
                          for root, dirs, files in os.walk(tools_dir) 
                          for file in files)
            
            if has_files:
                log_info(f"Tool integrity validated: {tool_id}")
                return True
            else:
                log_warning(f"Tool directory is empty: {tool_id}")
                return False
                
        except Exception as e:
            log_error(f"Error validating tool integrity: {e}")
            return False


def get_library_manager(base_path: str) -> LibraryManager:
    """
    Factory function to get a LibraryManager instance.
    
    Args:
        base_path: Base path of the Sunshine-AIO application
        
    Returns:
        LibraryManager: Configured LibraryManager instance
    """
    return LibraryManager(base_path)