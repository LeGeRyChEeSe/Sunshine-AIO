"""
Sunshine-AIO Community Library Integration Package

This package provides the core infrastructure for integrating community tools
from the sunshine-aio-library repository into the main Sunshine-AIO application.

Main Components:
- LibraryManager: Coordinates all library operations
- ToolProvider: Abstract interface for tool providers (static/dynamic)
- CacheManager: Local metadata and file caching
- ToolValidator: Security and compatibility validation

Usage:
    from library import get_library_manager, get_tool_validator
    
    # Initialize library components
    lib_manager = get_library_manager('/path/to/sunshine-aio')
    validator = get_tool_validator()
    
    # Get available tools
    tools = lib_manager.get_available_tools()
"""

__version__ = "1.0.0"
__author__ = "Sunshine-AIO Team"

# Core module imports
from .library_manager import LibraryManager, get_library_manager
from .tool_provider import (
    ToolProvider,
    ToolInfo,
    ToolSource,
    ToolStatus,
    StaticToolProvider,
    DynamicToolProvider
)
from .cache_manager import CacheManager, CacheEntry, get_cache_manager
from .validators import (
    ToolValidator,
    ValidationResult,
    ValidationLevel,
    get_tool_validator
)

# Import logging for proper initialization
from misc.Logger import log_info, log_error

# Package-level exports
__all__ = [
    # Main classes
    'LibraryManager',
    'ToolProvider',
    'CacheManager',
    'ToolValidator',
    
    # Data classes and enums
    'ToolInfo',
    'ToolSource',
    'ToolStatus',
    'CacheEntry',
    'ValidationResult',
    'ValidationLevel',
    
    # Provider implementations
    'StaticToolProvider',
    'DynamicToolProvider',
    
    # Factory functions
    'get_library_manager',
    'get_cache_manager',
    'get_tool_validator',
    
    # Utility functions
    'initialize_library_system',
    'get_library_info'
]


def initialize_library_system(base_path: str, config: dict = None) -> dict:
    """
    Initialize the complete library system with all components.
    
    This is a convenience function that sets up all the library components
    with proper integration and returns instances ready for use.
    
    Args:
        base_path: Base path of the Sunshine-AIO application
        config: Optional configuration dictionary
        
    Returns:
        dict: Dictionary containing initialized components:
            - library_manager: LibraryManager instance
            - cache_manager: CacheManager instance  
            - validator: ToolValidator instance
            - static_provider: StaticToolProvider instance
            - dynamic_provider: DynamicToolProvider instance
            
    Example:
        components = initialize_library_system('/path/to/sunshine-aio')
        lib_manager = components['library_manager']
        tools = lib_manager.get_available_tools()
    """
    try:
        log_info("Initializing Sunshine-AIO library system...")
        
        # Default configuration
        default_config = {
            'library': {
                'repository_url': 'https://github.com/LeGeRyChEeSe/sunshine-aio-library',
                'sync_interval': 3600,  # 1 hour
                'validation_enabled': True
            },
            'cache': {
                'default_ttl': 3600,
                'max_cache_size': 1024 * 1024 * 1024,  # 1GB
                'auto_cleanup': True
            },
            'validation': {
                'validation_level': 'standard',
                'checksum_required': True,
                'max_file_size': 100 * 1024 * 1024  # 100MB
            }
        }
        
        # Merge with provided config
        if config:
            for section, values in config.items():
                if section in default_config:
                    default_config[section].update(values)
                else:
                    default_config[section] = values
        
        # Initialize cache manager
        cache_dir = os.path.join(base_path, "cache", "library")
        cache_manager = get_cache_manager(cache_dir, default_config.get('cache'))
        log_info("Cache manager initialized")
        
        # Initialize validator
        validator = get_tool_validator(default_config.get('validation'))
        log_info("Tool validator initialized")
        
        # Initialize library manager
        lib_config = default_config.get('library', {})
        library_manager = LibraryManager(
            base_path=base_path,
            repository_url=lib_config.get('repository_url'),
            cache_dir=cache_dir
        )
        
        # Initialize library manager
        if not library_manager.initialize():
            log_error("Failed to initialize library manager")
            raise RuntimeError("Library manager initialization failed")
        
        log_info("Library manager initialized")
        
        # Initialize tool providers
        static_provider = StaticToolProvider()
        static_provider.initialize()
        log_info("Static tool provider initialized")
        
        dynamic_provider = DynamicToolProvider(library_manager)
        dynamic_provider.initialize()
        log_info("Dynamic tool provider initialized")
        
        components = {
            'library_manager': library_manager,
            'cache_manager': cache_manager,
            'validator': validator,
            'static_provider': static_provider,
            'dynamic_provider': dynamic_provider
        }
        
        log_info("Library system initialization completed successfully")
        return components
        
    except Exception as e:
        log_error(f"Failed to initialize library system: {e}")
        raise


def get_library_info() -> dict:
    """
    Get information about the library package.
    
    Returns:
        dict: Library package information
    """
    import os
    
    return {
        'name': 'sunshine-aio-library-integration',
        'version': __version__,
        'author': __author__,
        'description': 'Community library integration for Sunshine-AIO',
        'components': {
            'LibraryManager': 'Coordinates all library operations',
            'ToolProvider': 'Abstract interface for tool providers',
            'CacheManager': 'Local metadata and file caching',
            'ToolValidator': 'Security and compatibility validation'
        },
        'supported_features': [
            'Dynamic tool discovery',
            'Automatic caching',
            'Security validation',
            'Platform compatibility checks',
            'Checksum verification',
            'Metadata synchronization'
        ]
    }


# Import os after defining functions to avoid circular imports
import os

# Initialize logging for the package
log_info("Sunshine-AIO Library Integration package loaded")