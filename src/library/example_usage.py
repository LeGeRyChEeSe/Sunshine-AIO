#!/usr/bin/env python3
"""
Example usage of the Sunshine-AIO Library Integration system.

This example demonstrates how to use the library components to:
1. Initialize the library system
2. Fetch and validate community tools
3. Search for specific tools
4. Cache tool metadata

Note: This is an example file for demonstration purposes.
Do not run this directly without proper setup.
"""

import os
import sys
from typing import Dict, Any

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from library import (
    initialize_library_system,
    get_library_manager,
    get_tool_validator,
    ValidationLevel
)


def example_basic_usage():
    """Example of basic library usage."""
    print("=== Basic Library Usage Example ===")
    
    # Initialize the library system
    base_path = os.path.dirname(os.path.dirname(__file__))  # src directory
    
    try:
        # Get library manager
        lib_manager = get_library_manager(base_path)
        
        # Initialize the library manager
        if not lib_manager.initialize():
            print("Failed to initialize library manager")
            return
        
        # Get available tools
        tools = lib_manager.get_available_tools()
        print(f"Found {len(tools)} available tools:")
        
        for tool_id, tool_info in tools.items():
            print(f"  - {tool_id}: {tool_info.get('name', 'Unknown')}")
            print(f"    Category: {tool_info.get('category', 'General')}")
            print(f"    Description: {tool_info.get('description', 'No description')[:50]}...")
            print()
        
    except Exception as e:
        print(f"Error: {e}")


def example_tool_validation():
    """Example of tool validation."""
    print("=== Tool Validation Example ===")
    
    # Get validator with strict validation
    validator = get_tool_validator({
        'validation_level': ValidationLevel.STRICT.value,
        'checksum_required': True
    })
    
    # Example tool metadata
    sample_tool = {
        'id': 'example-tool',
        'name': 'Example Tool',
        'version': '1.2.3',
        'description': 'A sample tool for demonstration',
        'author': 'Community Developer',
        'category': 'Utilities',
        'platform_support': ['windows', 'linux'],
        'dependencies': ['python>=3.8'],
        'checksum': 'abc123def456',
        'size': 1024000
    }
    
    try:
        # Validate the tool
        result = validator.validate_tool(sample_tool)
        
        print(f"Validation Result: {'PASSED' if result.is_valid else 'FAILED'}")
        print(f"Security Score: {result.security_score:.2f}")
        
        if result.messages:
            print("Messages:")
            for msg in result.messages:
                print(f"  ✓ {msg}")
        
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  ⚠ {warning}")
        
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  ✗ {error}")
        
    except Exception as e:
        print(f"Validation error: {e}")


def example_tool_search():
    """Example of tool search functionality."""
    print("=== Tool Search Example ===")
    
    base_path = os.path.dirname(os.path.dirname(__file__))
    
    try:
        lib_manager = get_library_manager(base_path)
        lib_manager.initialize()
        
        # Search for tools
        search_queries = ['utility', 'game', 'media']
        
        for query in search_queries:
            print(f"Searching for '{query}':")
            results = lib_manager.search_tools(query)
            
            if results:
                for tool_id, tool_info in results.items():
                    print(f"  - {tool_id}: {tool_info.get('name', 'Unknown')}")
            else:
                print("  No results found")
            print()
        
        # Get categories
        categories = lib_manager.get_categories()
        print(f"Available categories: {', '.join(categories)}")
        
    except Exception as e:
        print(f"Search error: {e}")


def example_complete_workflow():
    """Example of complete library workflow."""
    print("=== Complete Workflow Example ===")
    
    base_path = os.path.dirname(os.path.dirname(__file__))
    
    try:
        # Initialize complete system
        config = {
            'library': {
                'repository_url': 'https://github.com/LeGeRyChEeSe/sunshine-aio-library',
                'validation_enabled': True
            },
            'validation': {
                'validation_level': 'standard'
            }
        }
        
        components = initialize_library_system(base_path, config)
        
        lib_manager = components['library_manager']
        validator = components['validator']
        
        print("System initialized successfully!")
        
        # Get sync status
        status = lib_manager.get_sync_status()
        print(f"Sync status: {status}")
        
        # Force sync if needed
        if status.get('sync_needed', False):
            print("Syncing library metadata...")
            success = lib_manager.force_sync()
            print(f"Sync {'successful' if success else 'failed'}")
        
        # Get tools and validate one
        tools = lib_manager.get_available_tools()
        if tools:
            tool_id = list(tools.keys())[0]
            tool_info = tools[tool_id]
            
            print(f"Validating tool: {tool_id}")
            result = validator.validate_tool(tool_info)
            print(f"Validation: {'PASSED' if result.is_valid else 'FAILED'}")
        
    except Exception as e:
        print(f"Workflow error: {e}")


def example_cache_usage():
    """Example of cache manager usage."""
    print("=== Cache Manager Example ===")
    
    from library import get_cache_manager
    
    cache_dir = "/tmp/sunshine-aio-cache-example"
    
    try:
        cache_manager = get_cache_manager(cache_dir)
        
        # Cache some data
        cache_manager.set("test_key", {"data": "example"}, ttl=60)
        
        # Retrieve cached data
        cached_data = cache_manager.get("test_key")
        print(f"Cached data: {cached_data}")
        
        # Cache a file
        test_content = b"This is test file content"
        cached_file = cache_manager.cache_file(
            "/example/path/test.txt", 
            test_content,
            key="test_file"
        )
        print(f"File cached to: {cached_file}")
        
        # Get cache stats
        stats = cache_manager.get_stats()
        print(f"Cache stats: {stats}")
        
        # Clean up
        cache_manager.clear()
        print("Cache cleared")
        
    except Exception as e:
        print(f"Cache error: {e}")


if __name__ == "__main__":
    """Run all examples."""
    examples = [
        example_basic_usage,
        example_tool_validation,
        example_tool_search,
        example_cache_usage,
        # example_complete_workflow  # Commented out as it requires network access
    ]
    
    for example in examples:
        try:
            example()
            print("-" * 50)
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")
            print("-" * 50)