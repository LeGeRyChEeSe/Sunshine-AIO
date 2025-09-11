"""
Tool Provider Abstract Interface for Sunshine-AIO Library Integration

This module defines the abstract base class and interfaces for tool providers,
supporting both static (built-in) and dynamic (community) tool sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import os

from misc.Logger import log_info, log_error, log_warning


class ToolSource(Enum):
    """Enumeration of tool source types."""
    STATIC = "static"       # Built-in tools
    DYNAMIC = "dynamic"     # Community library tools
    LOCAL = "local"         # Local custom tools
    CACHED = "cached"       # Cached remote tools


class ToolStatus(Enum):
    """Enumeration of tool installation/availability status."""
    AVAILABLE = "available"           # Tool is available for installation
    INSTALLED = "installed"           # Tool is currently installed
    INSTALLING = "installing"         # Tool installation in progress
    FAILED = "failed"                # Tool installation failed
    OUTDATED = "outdated"            # Tool has updates available
    CORRUPTED = "corrupted"          # Tool files are corrupted
    UNAVAILABLE = "unavailable"      # Tool is not available


class ToolInfo:
    """
    Data class representing tool information and metadata.
    """
    
    def __init__(self, 
                 tool_id: str,
                 name: str,
                 description: str = "",
                 version: str = "1.0.0",
                 category: str = "General",
                 source: ToolSource = ToolSource.DYNAMIC,
                 status: ToolStatus = ToolStatus.AVAILABLE,
                 **kwargs):
        """
        Initialize tool information.
        
        Args:
            tool_id: Unique identifier for the tool
            name: Human-readable tool name
            description: Tool description
            version: Tool version
            category: Tool category
            source: Tool source type
            status: Tool status
            **kwargs: Additional metadata
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.version = version
        self.category = category
        self.source = source
        self.status = status
        
        # Additional metadata
        self.author = kwargs.get('author', 'Unknown')
        self.size = kwargs.get('size', 0)
        self.download_url = kwargs.get('download_url')
        self.dependencies = kwargs.get('dependencies', [])
        self.platform_support = kwargs.get('platform_support', ['windows'])
        self.last_updated = kwargs.get('last_updated')
        self.checksum = kwargs.get('checksum')
        self.tags = kwargs.get('tags', [])
        self.rating = kwargs.get('rating', 0.0)
        self.installation_path = kwargs.get('installation_path')
        
        # Validation flags
        self.validated = kwargs.get('validated', False)
        self.trusted = kwargs.get('trusted', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ToolInfo to dictionary representation."""
        return {
            'tool_id': self.tool_id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'category': self.category,
            'source': self.source.value,
            'status': self.status.value,
            'author': self.author,
            'size': self.size,
            'download_url': self.download_url,
            'dependencies': self.dependencies,
            'platform_support': self.platform_support,
            'last_updated': self.last_updated,
            'checksum': self.checksum,
            'tags': self.tags,
            'rating': self.rating,
            'installation_path': self.installation_path,
            'validated': self.validated,
            'trusted': self.trusted
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolInfo':
        """Create ToolInfo instance from dictionary."""
        tool_id = data.get('tool_id', data.get('id', ''))
        name = data.get('name', tool_id)
        description = data.get('description', '')
        version = data.get('version', '1.0.0')
        category = data.get('category', 'General')
        
        # Convert string enums back to enum objects
        source_str = data.get('source', 'dynamic')
        source = ToolSource(source_str) if source_str in [s.value for s in ToolSource] else ToolSource.DYNAMIC
        
        status_str = data.get('status', 'available')
        status = ToolStatus(status_str) if status_str in [s.value for s in ToolStatus] else ToolStatus.AVAILABLE
        
        # Pass remaining data as kwargs
        kwargs = {k: v for k, v in data.items() 
                 if k not in ['tool_id', 'id', 'name', 'description', 'version', 'category', 'source', 'status']}
        
        return cls(tool_id, name, description, version, category, source, status, **kwargs)
    
    def is_compatible_platform(self, platform: str = None) -> bool:
        """
        Check if tool is compatible with the given platform.
        
        Args:
            platform: Platform to check (defaults to current platform)
            
        Returns:
            bool: True if compatible
        """
        if platform is None:
            import sys
            platform = sys.platform
        
        if platform.startswith('win'):
            platform = 'windows'
        elif platform.startswith('linux'):
            platform = 'linux'
        elif platform.startswith('darwin'):
            platform = 'macos'
        
        return platform in self.platform_support or 'all' in self.platform_support


class ToolProvider(ABC):
    """
    Abstract base class for tool providers.
    
    This interface defines the contract that all tool providers must implement,
    whether they serve static built-in tools or dynamic community tools.
    """
    
    def __init__(self, provider_id: str, provider_name: str):
        """
        Initialize the tool provider.
        
        Args:
            provider_id: Unique identifier for this provider
            provider_name: Human-readable provider name
        """
        self.provider_id = provider_id
        self.provider_name = provider_name
        self._initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the tool provider.
        
        Returns:
            bool: True if initialization was successful
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> Dict[str, ToolInfo]:
        """
        Get all available tools from this provider.
        
        Returns:
            Dict mapping tool IDs to ToolInfo objects
        """
        pass
    
    @abstractmethod
    def get_tool_info(self, tool_id: str) -> Optional[ToolInfo]:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_id: ID of the tool to get info for
            
        Returns:
            ToolInfo object or None if tool not found
        """
        pass
    
    @abstractmethod
    def install_tool(self, tool_id: str, **kwargs) -> bool:
        """
        Install a specific tool.
        
        Args:
            tool_id: ID of the tool to install
            **kwargs: Additional installation parameters
            
        Returns:
            bool: True if installation was successful
        """
        pass
    
    def is_tool_available(self, tool_id: str) -> bool:
        """
        Check if a tool is available from this provider.
        
        Args:
            tool_id: ID of the tool to check
            
        Returns:
            bool: True if tool is available
        """
        return tool_id in self.get_tools()
    
    def search_tools(self, query: str, **filters) -> Dict[str, ToolInfo]:
        """
        Search for tools matching a query and optional filters.
        
        Args:
            query: Search query string
            **filters: Additional search filters (category, tags, etc.)
            
        Returns:
            Dict of matching ToolInfo objects
        """
        tools = self.get_tools()
        results = {}
        
        query_lower = query.lower()
        category_filter = filters.get('category')
        tags_filter = filters.get('tags', [])
        
        for tool_id, tool_info in tools.items():
            # Check query match
            matches_query = (
                not query or
                query_lower in tool_id.lower() or
                query_lower in tool_info.name.lower() or
                query_lower in tool_info.description.lower()
            )
            
            # Check category filter
            matches_category = (
                not category_filter or
                tool_info.category.lower() == category_filter.lower()
            )
            
            # Check tags filter
            matches_tags = (
                not tags_filter or
                any(tag in tool_info.tags for tag in tags_filter)
            )
            
            if matches_query and matches_category and matches_tags:
                results[tool_id] = tool_info
        
        return results
    
    def get_categories(self) -> List[str]:
        """
        Get all available categories from this provider.
        
        Returns:
            List of category names
        """
        tools = self.get_tools()
        categories = set()
        
        for tool_info in tools.values():
            categories.add(tool_info.category)
        
        return sorted(list(categories))
    
    def get_provider_info(self) -> Dict[str, Any]:
        """
        Get information about this provider.
        
        Returns:
            Dict containing provider information
        """
        tools = self.get_tools()
        
        return {
            'provider_id': self.provider_id,
            'provider_name': self.provider_name,
            'initialized': self._initialized,
            'total_tools': len(tools),
            'categories': self.get_categories(),
            'source_type': self.__class__.__name__
        }


class StaticToolProvider(ToolProvider):
    """
    Tool provider for built-in/static tools.
    
    This provider manages tools that are bundled with the application
    and don't require dynamic downloading or installation.
    """
    
    def __init__(self, tools_config: Dict[str, Dict[str, Any]] = None):
        """
        Initialize static tool provider.
        
        Args:
            tools_config: Configuration dictionary for static tools
        """
        super().__init__("static", "Built-in Tools")
        self.tools_config = tools_config or {}
        self._static_tools: Dict[str, ToolInfo] = {}
    
    def initialize(self) -> bool:
        """Initialize the static tool provider."""
        try:
            log_info(f"Initializing {self.provider_name}...")
            
            # Load static tools from configuration
            self._load_static_tools()
            
            self._initialized = True
            log_info(f"Loaded {len(self._static_tools)} static tools")
            return True
            
        except Exception as e:
            log_error(f"Failed to initialize static tool provider: {e}")
            return False
    
    def _load_static_tools(self) -> None:
        """Load static tools from configuration."""
        for tool_id, tool_config in self.tools_config.items():
            try:
                tool_info = ToolInfo(
                    tool_id=tool_id,
                    name=tool_config.get('name', tool_id),
                    description=tool_config.get('description', ''),
                    version=tool_config.get('version', '1.0.0'),
                    category=tool_config.get('category', 'Built-in'),
                    source=ToolSource.STATIC,
                    status=ToolStatus.INSTALLED,
                    trusted=True,
                    validated=True,
                    **tool_config
                )
                self._static_tools[tool_id] = tool_info
                
            except Exception as e:
                log_warning(f"Failed to load static tool {tool_id}: {e}")
    
    def get_tools(self) -> Dict[str, ToolInfo]:
        """Get all static tools."""
        return self._static_tools.copy()
    
    def get_tool_info(self, tool_id: str) -> Optional[ToolInfo]:
        """Get info for a specific static tool."""
        return self._static_tools.get(tool_id)
    
    def install_tool(self, tool_id: str, **kwargs) -> bool:
        """
        Install a static tool (typically just marks as installed).
        
        Static tools are already available, so this mainly updates status.
        """
        if tool_id in self._static_tools:
            self._static_tools[tool_id].status = ToolStatus.INSTALLED
            log_info(f"Static tool {tool_id} marked as installed")
            return True
        
        log_error(f"Static tool {tool_id} not found")
        return False


class DynamicToolProvider(ToolProvider):
    """
    Tool provider for dynamic/community tools.
    
    This provider manages tools from external sources that need to be
    downloaded and installed dynamically.
    """
    
    def __init__(self, library_manager=None):
        """
        Initialize dynamic tool provider.
        
        Args:
            library_manager: LibraryManager instance for fetching tools
        """
        super().__init__("dynamic", "Community Library")
        self.library_manager = library_manager
        self._dynamic_tools: Dict[str, ToolInfo] = {}
    
    def initialize(self) -> bool:
        """Initialize the dynamic tool provider."""
        try:
            log_info(f"Initializing {self.provider_name}...")
            
            if self.library_manager:
                # Load tools from library manager
                self._load_dynamic_tools()
            
            self._initialized = True
            log_info(f"Loaded {len(self._dynamic_tools)} dynamic tools")
            return True
            
        except Exception as e:
            log_error(f"Failed to initialize dynamic tool provider: {e}")
            return False
    
    def _load_dynamic_tools(self) -> None:
        """Load dynamic tools from library manager."""
        if not self.library_manager:
            return
        
        try:
            tools_data = self.library_manager.get_available_tools()
            
            for tool_id, tool_data in tools_data.items():
                try:
                    tool_info = ToolInfo.from_dict(tool_data)
                    tool_info.source = ToolSource.DYNAMIC
                    self._dynamic_tools[tool_id] = tool_info
                    
                except Exception as e:
                    log_warning(f"Failed to load dynamic tool {tool_id}: {e}")
                    
        except Exception as e:
            log_error(f"Failed to load dynamic tools: {e}")
    
    def get_tools(self) -> Dict[str, ToolInfo]:
        """Get all dynamic tools."""
        return self._dynamic_tools.copy()
    
    def get_tool_info(self, tool_id: str) -> Optional[ToolInfo]:
        """Get info for a specific dynamic tool."""
        return self._dynamic_tools.get(tool_id)
    
    def install_tool(self, tool_id: str, **kwargs) -> bool:
        """
        Install a dynamic tool.
        
        This is a placeholder - actual installation logic would be
        implemented by the installer component.
        """
        if tool_id in self._dynamic_tools:
            # Mark as installing
            self._dynamic_tools[tool_id].status = ToolStatus.INSTALLING
            log_info(f"Starting installation of dynamic tool {tool_id}")
            
            # TODO: Implement actual installation logic
            # For now, just simulate success
            self._dynamic_tools[tool_id].status = ToolStatus.INSTALLED
            log_info(f"Dynamic tool {tool_id} installed successfully")
            return True
        
        log_error(f"Dynamic tool {tool_id} not found")
        return False
    
    def refresh_tools(self) -> bool:
        """
        Refresh the list of available dynamic tools.
        
        Returns:
            bool: True if refresh was successful
        """
        try:
            if self.library_manager:
                success = self.library_manager.sync_library_metadata()
                if success:
                    self._load_dynamic_tools()
                    log_info("Dynamic tools refreshed successfully")
                    return True
            
            log_warning("Failed to refresh dynamic tools")
            return False
            
        except Exception as e:
            log_error(f"Error refreshing dynamic tools: {e}")
            return False