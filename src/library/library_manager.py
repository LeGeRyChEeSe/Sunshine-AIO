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

from misc.Logger import log_info, log_error, log_warning, log_success


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
        Fetch metadata from the remote repository.
        
        Returns:
            Dict containing repository metadata or None on failure
        """
        try:
            # Construct API URL for repository contents
            api_url = self._get_repository_api_url()
            
            headers = {
                'User-Agent': self.config['user_agent'],
                'Accept': 'application/vnd.github.v3+json'
            }
            
            log_info(f"Fetching metadata from: {api_url}")
            
            response = requests.get(
                api_url,
                headers=headers,
                timeout=self.config['timeout']
            )
            
            response.raise_for_status()
            
            # Parse repository structure and build metadata
            contents = response.json()
            metadata = self._parse_repository_contents(contents)
            
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
    
    def _get_repository_api_url(self) -> str:
        """
        Convert repository URL to GitHub API URL.
        
        Returns:
            str: GitHub API URL for repository contents
        """
        # Extract owner and repo from GitHub URL
        if "github.com/" in self.repository_url:
            parts = self.repository_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                return f"https://api.github.com/repos/{owner}/{repo}/contents"
        
        # Fallback - assume it's already an API URL
        return self.repository_url
    
    def _parse_repository_contents(self, contents: List[Dict]) -> Dict[str, Any]:
        """
        Parse repository contents and build metadata structure.
        
        Args:
            contents: Repository contents from GitHub API
            
        Returns:
            Dict containing parsed metadata
        """
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'tools': {},
            'categories': {},
            'repository_info': {
                'url': self.repository_url,
                'total_tools': 0
            }
        }
        
        try:
            # Look for tool directories or metadata files
            for item in contents:
                if item['type'] == 'dir':
                    # Assume each directory is a tool
                    tool_id = item['name']
                    metadata['tools'][tool_id] = {
                        'id': tool_id,
                        'name': tool_id.replace('_', ' ').replace('-', ' ').title(),
                        'path': item['path'],
                        'download_url': item.get('download_url'),
                        'size': item.get('size', 0),
                        'last_modified': item.get('updated_at', datetime.now().isoformat()),
                        'category': 'General',  # Default category
                        'description': f'Community tool: {tool_id}',
                        'version': '1.0.0',  # Default version
                        'validated': False
                    }
                
                elif item['name'].endswith('.json') and 'metadata' in item['name'].lower():
                    # Found metadata file - could contain tool information
                    log_info(f"Found potential metadata file: {item['name']}")
            
            metadata['repository_info']['total_tools'] = len(metadata['tools'])
            
            log_info(f"Parsed repository contents: {len(metadata['tools'])} tools found")
            return metadata
            
        except Exception as e:
            log_error(f"Error parsing repository contents: {e}")
            return metadata
    
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
        tools = self.get_available_tools()
        categories = set()
        
        for tool_info in tools.values():
            category = tool_info.get('category', 'General')
            categories.add(category)
        
        return sorted(list(categories))
    
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