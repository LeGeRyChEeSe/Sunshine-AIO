"""
Pytest fixtures and configuration for library integration tests.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import shutil
from typing import Dict, Any

# Import the library modules to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from library.library_manager import LibraryManager
from library.tool_provider import StaticToolProvider, DynamicToolProvider, ToolInfo, ToolSource, ToolStatus
from library.cache_manager import CacheManager, CacheEntry
from library.validators import ToolValidator, ValidationLevel, ValidationResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_base_path(temp_dir):
    """Mock base path for Sunshine-AIO."""
    return temp_dir


@pytest.fixture
def mock_cache_dir(temp_dir):
    """Mock cache directory."""
    cache_dir = os.path.join(temp_dir, "cache", "library")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


@pytest.fixture
def sample_tool_metadata():
    """Sample tool metadata for testing."""
    return {
        "last_updated": "2024-01-15T10:30:00",
        "tools": {
            "example_tool": {
                "id": "example_tool",
                "name": "Example Tool",
                "description": "A test tool for demonstration",
                "version": "1.0.0",
                "category": "Testing",
                "path": "tools/example_tool",
                "download_url": "https://example.com/tool.zip",
                "size": 1024,
                "last_modified": "2024-01-15T10:30:00",
                "validated": True,
                "checksum": "abc123def456",
                "platform_support": ["windows", "linux"],
                "dependencies": ["python>=3.8"],
                "author": "Test Author",
                "tags": ["test", "example"]
            },
            "secure_tool": {
                "id": "secure_tool",
                "name": "Secure Tool",
                "description": "A validated secure tool",
                "version": "2.1.0",
                "category": "Security",
                "path": "tools/secure_tool",
                "download_url": "https://example.com/secure.zip",
                "size": 2048,
                "last_modified": "2024-01-10T15:45:00",
                "validated": True,
                "trusted": True,
                "checksum": "def456ghi789",
                "platform_support": ["all"],
                "dependencies": [],
                "author": "Security Team",
                "tags": ["security", "validated"]
            }
        },
        "categories": {
            "Testing": ["example_tool"],
            "Security": ["secure_tool"]
        },
        "repository_info": {
            "url": "https://github.com/test/test-repo",
            "total_tools": 2
        }
    }


@pytest.fixture
def sample_invalid_metadata():
    """Sample invalid metadata for testing error handling."""
    return {
        "tools": {
            "invalid_tool": {
                "name": "Invalid Tool",
                # Missing required fields like id, version, etc.
            },
            "malicious_tool": {
                "id": "malicious_tool",
                "name": "Malicious Tool",
                "description": "A tool with security issues",
                "version": "1.0.0",
                "category": "Malware",
                "download_url": "javascript:alert('xss')",  # Invalid URL
                "checksum": "invalid_checksum_format",
                "platform_support": ["unknown_platform"],
                "validated": False,
                "trusted": False
            }
        }
    }


@pytest.fixture
def mock_github_api_response():
    """Mock GitHub API response for repository contents."""
    return [
        {
            "name": "example_tool",
            "type": "dir",
            "path": "tools/example_tool",
            "download_url": None,
            "size": 0,
            "updated_at": "2024-01-15T10:30:00Z"
        },
        {
            "name": "secure_tool",
            "type": "dir", 
            "path": "tools/secure_tool",
            "download_url": None,
            "size": 0,
            "updated_at": "2024-01-10T15:45:00Z"
        },
        {
            "name": "metadata.json",
            "type": "file",
            "path": "metadata.json",
            "download_url": "https://raw.githubusercontent.com/test/test-repo/main/metadata.json",
            "size": 1024,
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]


@pytest.fixture
def static_tools_config():
    """Configuration for static tools."""
    return {
        "built_in_tool": {
            "name": "Built-in Tool",
            "description": "A built-in tool",
            "version": "1.0.0",
            "category": "Built-in",
            "installation_path": "/builtin/tools/built_in_tool"
        },
        "core_utility": {
            "name": "Core Utility", 
            "description": "Essential core utility",
            "version": "2.0.0",
            "category": "Core",
            "installation_path": "/builtin/tools/core_utility",
            "dependencies": []
        }
    }


@pytest.fixture
def sample_tool_info():
    """Sample ToolInfo object."""
    return ToolInfo(
        tool_id="test_tool",
        name="Test Tool",
        description="A tool for testing",
        version="1.0.0",
        category="Testing",
        source=ToolSource.DYNAMIC,
        status=ToolStatus.AVAILABLE,
        author="Test Author",
        size=1024,
        download_url="https://example.com/tool.zip",
        dependencies=["python>=3.8"],
        platform_support=["windows", "linux"],
        checksum="abc123def456",
        tags=["test", "example"],
        validated=True
    )


@pytest.fixture
def mock_requests():
    """Mock requests module for HTTP calls."""
    with patch('requests.get') as mock_get:
        yield mock_get


@pytest.fixture
def library_manager(mock_base_path, mock_cache_dir):
    """LibraryManager instance for testing."""
    return LibraryManager(
        base_path=mock_base_path,
        repository_url="https://github.com/test/test-repo",
        cache_dir=mock_cache_dir
    )


@pytest.fixture
def static_tool_provider(static_tools_config):
    """StaticToolProvider instance for testing."""
    return StaticToolProvider(tools_config=static_tools_config)


@pytest.fixture
def dynamic_tool_provider(library_manager):
    """DynamicToolProvider instance for testing.""" 
    return DynamicToolProvider(library_manager=library_manager)


@pytest.fixture
def cache_manager(mock_cache_dir):
    """CacheManager instance for testing."""
    return CacheManager(cache_dir=mock_cache_dir)


@pytest.fixture
def tool_validator():
    """ToolValidator instance for testing."""
    return ToolValidator()


@pytest.fixture
def sample_cache_entries():
    """Sample cache entries for testing."""
    return {
        "test_key": CacheEntry(
            key="test_key",
            data={"test": "data"},
            ttl=3600
        ),
        "expired_key": CacheEntry(
            key="expired_key", 
            data={"expired": "data"},
            ttl=1,
            created_at=datetime.now() - timedelta(seconds=2)
        ),
        "persistent_key": CacheEntry(
            key="persistent_key",
            data={"persistent": "data"},
            ttl=86400
        )
    }


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('os.path.exists') as mock_exists, \
         patch('os.makedirs') as mock_makedirs, \
         patch('os.remove') as mock_remove, \
         patch('shutil.rmtree') as mock_rmtree:
        
        mock_exists.return_value = True
        yield {
            'exists': mock_exists,
            'makedirs': mock_makedirs, 
            'remove': mock_remove,
            'rmtree': mock_rmtree
        }


@pytest.fixture(autouse=True)
def mock_logger():
    """Mock the logger to prevent log output during tests."""
    with patch('misc.Logger.log_info'), \
         patch('misc.Logger.log_error'), \
         patch('misc.Logger.log_warning'), \
         patch('misc.Logger.log_success'):
        yield


@pytest.fixture
def validation_test_cases():
    """Test cases for validation testing."""
    return {
        "valid_tool": {
            "id": "valid_tool",
            "name": "Valid Tool",
            "description": "A valid tool",
            "version": "1.0.0",
            "category": "Testing",
            "download_url": "https://example.com/tool.zip",
            "checksum": "sha256:abcdef123456",
            "platform_support": ["windows", "linux"],
            "dependencies": ["python>=3.8"],
            "validated": True,
            "trusted": True
        },
        "invalid_url": {
            "id": "invalid_url_tool", 
            "name": "Invalid URL Tool",
            "description": "Tool with invalid URL",
            "version": "1.0.0",
            "category": "Testing",
            "download_url": "javascript:alert('xss')",
            "checksum": "sha256:123456abcdef",
            "platform_support": ["windows"],
            "dependencies": []
        },
        "missing_fields": {
            "name": "Incomplete Tool"
            # Missing required fields
        },
        "malicious_content": {
            "id": "malicious_tool",
            "name": "Malicious Tool",
            "description": "Contains malicious patterns",
            "version": "1.0.0",
            "category": "Malware",
            "download_url": "https://malicious-site.com/payload.exe",
            "checksum": "invalid_format",
            "platform_support": ["windows"],
            "dependencies": ["backdoor_lib"],
            "validated": False,
            "trusted": False
        }
    }


@pytest.fixture
def mock_network_error():
    """Simulate network errors for testing."""
    def raise_network_error(*args, **kwargs):
        import requests
        raise requests.ConnectionError("Network error")
    return raise_network_error


@pytest.fixture
def mock_timeout_error():
    """Simulate timeout errors for testing."""
    def raise_timeout_error(*args, **kwargs):
        import requests
        raise requests.Timeout("Request timeout")
    return raise_timeout_error