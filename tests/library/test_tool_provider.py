"""
Comprehensive unit tests for ToolProvider classes.

Tests cover the abstract ToolProvider interface, ToolInfo data class,
StaticToolProvider and DynamicToolProvider implementations, search functionality,
and platform compatibility checks.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from library.tool_provider import (
    ToolProvider, StaticToolProvider, DynamicToolProvider,
    ToolInfo, ToolSource, ToolStatus
)


class TestToolInfoDataClass:
    """Test ToolInfo data class functionality."""
    
    def test_tool_info_initialization_basic(self):
        """Test basic ToolInfo initialization."""
        tool = ToolInfo(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool"
        )
        
        assert tool.tool_id == "test_tool"
        assert tool.name == "Test Tool"
        assert tool.description == "A test tool"
        assert tool.version == "1.0.0"
        assert tool.category == "General"
        assert tool.source == ToolSource.DYNAMIC
        assert tool.status == ToolStatus.AVAILABLE
    
    def test_tool_info_initialization_full(self):
        """Test ToolInfo initialization with all parameters."""
        tool = ToolInfo(
            tool_id="full_tool",
            name="Full Tool",
            description="A complete tool",
            version="2.1.0",
            category="Development",
            source=ToolSource.STATIC,
            status=ToolStatus.INSTALLED,
            author="Developer",
            size=2048,
            download_url="https://example.com/tool.zip",
            dependencies=["python>=3.8"],
            platform_support=["windows", "linux"],
            checksum="abc123",
            tags=["dev", "tool"],
            rating=4.5,
            validated=True,
            trusted=True
        )
        
        assert tool.tool_id == "full_tool"
        assert tool.name == "Full Tool"
        assert tool.version == "2.1.0"
        assert tool.category == "Development"
        assert tool.source == ToolSource.STATIC
        assert tool.status == ToolStatus.INSTALLED
        assert tool.author == "Developer"
        assert tool.size == 2048
        assert tool.download_url == "https://example.com/tool.zip"
        assert tool.dependencies == ["python>=3.8"]
        assert tool.platform_support == ["windows", "linux"]
        assert tool.checksum == "abc123"
        assert tool.tags == ["dev", "tool"]
        assert tool.rating == 4.5
        assert tool.validated is True
        assert tool.trusted is True
    
    def test_tool_info_to_dict(self, sample_tool_info):
        """Test ToolInfo to_dict conversion."""
        tool_dict = sample_tool_info.to_dict()
        
        assert isinstance(tool_dict, dict)
        assert tool_dict['tool_id'] == sample_tool_info.tool_id
        assert tool_dict['name'] == sample_tool_info.name
        assert tool_dict['source'] == sample_tool_info.source.value
        assert tool_dict['status'] == sample_tool_info.status.value
        assert tool_dict['author'] == sample_tool_info.author
        assert tool_dict['validated'] == sample_tool_info.validated
    
    def test_tool_info_from_dict_basic(self):
        """Test ToolInfo from_dict creation with basic data."""
        data = {
            "tool_id": "dict_tool",
            "name": "Dict Tool",
            "description": "Tool from dict"
        }
        
        tool = ToolInfo.from_dict(data)
        
        assert tool.tool_id == "dict_tool"
        assert tool.name == "Dict Tool"
        assert tool.description == "Tool from dict"
        assert tool.version == "1.0.0"  # Default
        assert tool.source == ToolSource.DYNAMIC  # Default
    
    def test_tool_info_from_dict_full(self):
        """Test ToolInfo from_dict creation with full data."""
        data = {
            "id": "full_dict_tool",  # Test 'id' fallback
            "name": "Full Dict Tool",
            "description": "Complete tool from dict",
            "version": "3.0.0",
            "category": "Testing",
            "source": "static",
            "status": "installed",
            "author": "Dict Developer",
            "size": 4096,
            "download_url": "https://example.com/dict-tool.zip",
            "dependencies": ["requests"],
            "platform_support": ["all"],
            "checksum": "def456",
            "tags": ["dict", "test"],
            "rating": 3.8,
            "validated": True,
            "trusted": False
        }
        
        tool = ToolInfo.from_dict(data)
        
        assert tool.tool_id == "full_dict_tool"
        assert tool.name == "Full Dict Tool"
        assert tool.version == "3.0.0"
        assert tool.category == "Testing"
        assert tool.source == ToolSource.STATIC
        assert tool.status == ToolStatus.INSTALLED
        assert tool.author == "Dict Developer"
        assert tool.size == 4096
        assert tool.validated is True
        assert tool.trusted is False
    
    def test_tool_info_from_dict_invalid_enums(self):
        """Test ToolInfo from_dict with invalid enum values."""
        data = {
            "tool_id": "invalid_enum_tool",
            "name": "Invalid Enum Tool",
            "source": "invalid_source",
            "status": "invalid_status"
        }
        
        tool = ToolInfo.from_dict(data)
        
        assert tool.source == ToolSource.DYNAMIC  # Default fallback
        assert tool.status == ToolStatus.AVAILABLE  # Default fallback
    
    def test_tool_info_platform_compatibility_current(self, sample_tool_info):
        """Test platform compatibility check with current platform."""
        # Mock the current platform
        with patch('sys.platform', 'linux'):
            assert sample_tool_info.is_compatible_platform() is True
    
    def test_tool_info_platform_compatibility_specific(self, sample_tool_info):
        """Test platform compatibility check with specific platform."""
        assert sample_tool_info.is_compatible_platform('windows') is True
        assert sample_tool_info.is_compatible_platform('linux') is True
        assert sample_tool_info.is_compatible_platform('darwin') is False
    
    def test_tool_info_platform_compatibility_all_supported(self):
        """Test platform compatibility with 'all' support."""
        tool = ToolInfo(
            tool_id="cross_platform_tool",
            name="Cross Platform Tool",
            platform_support=["all"]
        )
        
        assert tool.is_compatible_platform('windows') is True
        assert tool.is_compatible_platform('linux') is True
        assert tool.is_compatible_platform('darwin') is True
    
    def test_tool_info_platform_name_conversion(self):
        """Test platform name conversion logic."""
        tool = ToolInfo(
            tool_id="platform_test",
            name="Platform Test Tool",
            platform_support=["windows", "linux", "macos"]
        )
        
        assert tool.is_compatible_platform('win32') is True  # Windows
        assert tool.is_compatible_platform('linux2') is True  # Linux
        assert tool.is_compatible_platform('darwin') is True   # macOS


class TestStaticToolProvider:
    """Test StaticToolProvider implementation."""
    
    def test_static_tool_provider_initialization(self, static_tools_config):
        """Test StaticToolProvider initialization."""
        provider = StaticToolProvider(tools_config=static_tools_config)
        
        assert provider.provider_id == "static"
        assert provider.provider_name == "Built-in Tools"
        assert provider.tools_config == static_tools_config
        assert not provider._initialized
        assert provider._static_tools == {}
    
    def test_static_tool_provider_initialization_empty(self):
        """Test StaticToolProvider initialization with empty config."""
        provider = StaticToolProvider()
        
        assert provider.tools_config == {}
        assert provider._static_tools == {}
    
    def test_static_tool_provider_initialize_success(self, static_tools_config):
        """Test successful StaticToolProvider initialization."""
        provider = StaticToolProvider(tools_config=static_tools_config)
        
        result = provider.initialize()
        
        assert result is True
        assert provider._initialized is True
        assert len(provider._static_tools) == len(static_tools_config)
        
        # Check that tools were loaded correctly
        for tool_id in static_tools_config:
            assert tool_id in provider._static_tools
            tool = provider._static_tools[tool_id]
            assert isinstance(tool, ToolInfo)
            assert tool.tool_id == tool_id
            assert tool.source == ToolSource.STATIC
            assert tool.status == ToolStatus.INSTALLED
            assert tool.validated is True
            assert tool.trusted is True
    
    def test_static_tool_provider_initialize_with_invalid_config(self):
        """Test StaticToolProvider initialization with invalid tool config."""
        invalid_config = {
            "invalid_tool": {
                "name": "Invalid Tool"
                # Missing other required fields
            },
            "valid_tool": {
                "name": "Valid Tool",
                "description": "A valid tool",
                "version": "1.0.0"
            }
        }
        
        provider = StaticToolProvider(tools_config=invalid_config)
        result = provider.initialize()
        
        # Should still succeed but skip invalid tools
        assert result is True
        assert "valid_tool" in provider._static_tools
        # Invalid tool should not be loaded (or loaded with defaults)
    
    def test_static_tool_provider_initialize_exception(self, static_tools_config):
        """Test StaticToolProvider initialization with exception."""
        with patch.object(StaticToolProvider, '_load_static_tools', side_effect=Exception("Load error")):
            provider = StaticToolProvider(tools_config=static_tools_config)
            
            result = provider.initialize()
            
            assert result is False
            assert not provider._initialized
    
    def test_static_tool_provider_get_tools(self, static_tool_provider):
        """Test StaticToolProvider get_tools method."""
        static_tool_provider.initialize()
        
        tools = static_tool_provider.get_tools()
        
        assert isinstance(tools, dict)
        assert len(tools) >= 2
        
        # Should return a copy, not the original
        tools["new_tool"] = "test"
        assert "new_tool" not in static_tool_provider._static_tools
    
    def test_static_tool_provider_get_tool_info_existing(self, static_tool_provider):
        """Test StaticToolProvider get_tool_info for existing tool."""
        static_tool_provider.initialize()
        
        tool_info = static_tool_provider.get_tool_info("built_in_tool")
        
        assert tool_info is not None
        assert isinstance(tool_info, ToolInfo)
        assert tool_info.tool_id == "built_in_tool"
        assert tool_info.name == "Built-in Tool"
    
    def test_static_tool_provider_get_tool_info_nonexistent(self, static_tool_provider):
        """Test StaticToolProvider get_tool_info for non-existent tool."""
        static_tool_provider.initialize()
        
        tool_info = static_tool_provider.get_tool_info("nonexistent_tool")
        
        assert tool_info is None
    
    def test_static_tool_provider_install_tool_existing(self, static_tool_provider):
        """Test StaticToolProvider install_tool for existing tool."""
        static_tool_provider.initialize()
        
        result = static_tool_provider.install_tool("built_in_tool")
        
        assert result is True
        tool = static_tool_provider._static_tools["built_in_tool"]
        assert tool.status == ToolStatus.INSTALLED
    
    def test_static_tool_provider_install_tool_nonexistent(self, static_tool_provider):
        """Test StaticToolProvider install_tool for non-existent tool."""
        static_tool_provider.initialize()
        
        result = static_tool_provider.install_tool("nonexistent_tool")
        
        assert result is False
    
    def test_static_tool_provider_is_tool_available(self, static_tool_provider):
        """Test StaticToolProvider is_tool_available method."""
        static_tool_provider.initialize()
        
        assert static_tool_provider.is_tool_available("built_in_tool") is True
        assert static_tool_provider.is_tool_available("nonexistent_tool") is False
    
    def test_static_tool_provider_get_categories(self, static_tool_provider):
        """Test StaticToolProvider get_categories method."""
        static_tool_provider.initialize()
        
        categories = static_tool_provider.get_categories()
        
        assert isinstance(categories, list)
        assert len(categories) >= 2
        assert "Built-in" in categories
        assert "Core" in categories
        assert categories == sorted(categories)  # Should be sorted
    
    def test_static_tool_provider_get_provider_info(self, static_tool_provider):
        """Test StaticToolProvider get_provider_info method."""
        static_tool_provider.initialize()
        
        info = static_tool_provider.get_provider_info()
        
        assert info['provider_id'] == "static"
        assert info['provider_name'] == "Built-in Tools"
        assert info['initialized'] is True
        assert info['total_tools'] >= 2
        assert isinstance(info['categories'], list)
        assert info['source_type'] == "StaticToolProvider"


class TestDynamicToolProvider:
    """Test DynamicToolProvider implementation."""
    
    def test_dynamic_tool_provider_initialization(self, library_manager):
        """Test DynamicToolProvider initialization."""
        provider = DynamicToolProvider(library_manager=library_manager)
        
        assert provider.provider_id == "dynamic"
        assert provider.provider_name == "Community Library"
        assert provider.library_manager == library_manager
        assert not provider._initialized
        assert provider._dynamic_tools == {}
    
    def test_dynamic_tool_provider_initialization_no_manager(self):
        """Test DynamicToolProvider initialization without library manager."""
        provider = DynamicToolProvider()
        
        assert provider.library_manager is None
        assert provider._dynamic_tools == {}
    
    def test_dynamic_tool_provider_initialize_success(self, dynamic_tool_provider, sample_tool_metadata):
        """Test successful DynamicToolProvider initialization."""
        # Mock library manager
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        
        result = dynamic_tool_provider.initialize()
        
        assert result is True
        assert dynamic_tool_provider._initialized is True
        assert len(dynamic_tool_provider._dynamic_tools) == len(sample_tool_metadata['tools'])
    
    def test_dynamic_tool_provider_initialize_no_manager(self):
        """Test DynamicToolProvider initialization without library manager."""
        provider = DynamicToolProvider()
        
        result = provider.initialize()
        
        assert result is True
        assert provider._initialized is True
        assert provider._dynamic_tools == {}
    
    def test_dynamic_tool_provider_initialize_exception(self, dynamic_tool_provider):
        """Test DynamicToolProvider initialization with exception."""
        with patch.object(DynamicToolProvider, '_load_dynamic_tools', side_effect=Exception("Load error")):
            result = dynamic_tool_provider.initialize()
            
            assert result is False
            assert not dynamic_tool_provider._initialized
    
    def test_dynamic_tool_provider_load_dynamic_tools(self, dynamic_tool_provider, sample_tool_metadata):
        """Test loading dynamic tools from library manager."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        
        dynamic_tool_provider._load_dynamic_tools()
        
        assert len(dynamic_tool_provider._dynamic_tools) == len(sample_tool_metadata['tools'])
        
        # Check that tools were converted correctly
        for tool_id, tool_data in sample_tool_metadata['tools'].items():
            assert tool_id in dynamic_tool_provider._dynamic_tools
            tool = dynamic_tool_provider._dynamic_tools[tool_id]
            assert isinstance(tool, ToolInfo)
            assert tool.tool_id == tool_id
            assert tool.source == ToolSource.DYNAMIC
    
    def test_dynamic_tool_provider_load_dynamic_tools_with_invalid_data(self, dynamic_tool_provider):
        """Test loading dynamic tools with invalid data."""
        invalid_tools = {
            "valid_tool": {
                "id": "valid_tool",
                "name": "Valid Tool",
                "description": "A valid tool"
            },
            "invalid_tool": {
                # Invalid data that might cause ToolInfo.from_dict to fail
                "id": None,
                "name": ["not", "a", "string"]
            }
        }
        
        dynamic_tool_provider.library_manager.get_available_tools.return_value = invalid_tools
        
        dynamic_tool_provider._load_dynamic_tools()
        
        # Should handle invalid tools gracefully
        assert "valid_tool" in dynamic_tool_provider._dynamic_tools
    
    def test_dynamic_tool_provider_get_tools(self, dynamic_tool_provider, sample_tool_metadata):
        """Test DynamicToolProvider get_tools method."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        tools = dynamic_tool_provider.get_tools()
        
        assert isinstance(tools, dict)
        assert len(tools) == len(sample_tool_metadata['tools'])
        
        # Should return a copy, not the original
        tools["new_tool"] = "test"
        assert "new_tool" not in dynamic_tool_provider._dynamic_tools
    
    def test_dynamic_tool_provider_get_tool_info_existing(self, dynamic_tool_provider, sample_tool_metadata):
        """Test DynamicToolProvider get_tool_info for existing tool."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        tool_info = dynamic_tool_provider.get_tool_info("example_tool")
        
        assert tool_info is not None
        assert isinstance(tool_info, ToolInfo)
        assert tool_info.tool_id == "example_tool"
    
    def test_dynamic_tool_provider_get_tool_info_nonexistent(self, dynamic_tool_provider, sample_tool_metadata):
        """Test DynamicToolProvider get_tool_info for non-existent tool."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        tool_info = dynamic_tool_provider.get_tool_info("nonexistent_tool")
        
        assert tool_info is None
    
    def test_dynamic_tool_provider_install_tool_existing(self, dynamic_tool_provider, sample_tool_metadata):
        """Test DynamicToolProvider install_tool for existing tool."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        result = dynamic_tool_provider.install_tool("example_tool")
        
        assert result is True
        tool = dynamic_tool_provider._dynamic_tools["example_tool"]
        assert tool.status == ToolStatus.INSTALLED
    
    def test_dynamic_tool_provider_install_tool_nonexistent(self, dynamic_tool_provider, sample_tool_metadata):
        """Test DynamicToolProvider install_tool for non-existent tool."""
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        result = dynamic_tool_provider.install_tool("nonexistent_tool")
        
        assert result is False
    
    def test_dynamic_tool_provider_refresh_tools_success(self, dynamic_tool_provider):
        """Test DynamicToolProvider refresh_tools success."""
        dynamic_tool_provider.library_manager.sync_library_metadata.return_value = True
        dynamic_tool_provider.library_manager.get_available_tools.return_value = {}
        
        result = dynamic_tool_provider.refresh_tools()
        
        assert result is True
        dynamic_tool_provider.library_manager.sync_library_metadata.assert_called_once()
    
    def test_dynamic_tool_provider_refresh_tools_failure(self, dynamic_tool_provider):
        """Test DynamicToolProvider refresh_tools failure."""
        dynamic_tool_provider.library_manager.sync_library_metadata.return_value = False
        
        result = dynamic_tool_provider.refresh_tools()
        
        assert result is False
    
    def test_dynamic_tool_provider_refresh_tools_no_manager(self):
        """Test DynamicToolProvider refresh_tools without library manager."""
        provider = DynamicToolProvider()
        
        result = provider.refresh_tools()
        
        assert result is False
    
    def test_dynamic_tool_provider_refresh_tools_exception(self, dynamic_tool_provider):
        """Test DynamicToolProvider refresh_tools with exception."""
        dynamic_tool_provider.library_manager.sync_library_metadata.side_effect = Exception("Sync error")
        
        result = dynamic_tool_provider.refresh_tools()
        
        assert result is False


class TestToolProviderAbstractMethods:
    """Test ToolProvider abstract base class functionality."""
    
    def test_tool_provider_search_tools_basic(self, static_tool_provider):
        """Test basic tool search functionality."""
        static_tool_provider.initialize()
        
        results = static_tool_provider.search_tools("built")
        
        assert isinstance(results, dict)
        assert len(results) >= 1
        assert "built_in_tool" in results
    
    def test_tool_provider_search_tools_empty_query(self, static_tool_provider):
        """Test tool search with empty query (should return all)."""
        static_tool_provider.initialize()
        
        results = static_tool_provider.search_tools("")
        
        # Empty query should return all tools
        all_tools = static_tool_provider.get_tools()
        assert len(results) == len(all_tools)
    
    def test_tool_provider_search_tools_category_filter(self, static_tool_provider):
        """Test tool search with category filter."""
        static_tool_provider.initialize()
        
        results = static_tool_provider.search_tools("", category="Built-in")
        
        assert len(results) >= 1
        for tool in results.values():
            assert tool.category == "Built-in"
    
    def test_tool_provider_search_tools_tags_filter(self, dynamic_tool_provider, sample_tool_metadata):
        """Test tool search with tags filter."""
        # Create a tool with tags for testing
        test_tools = {
            "tagged_tool": {
                "id": "tagged_tool",
                "name": "Tagged Tool",
                "description": "Tool with tags",
                "tags": ["test", "example"]
            }
        }
        
        dynamic_tool_provider.library_manager.get_available_tools.return_value = test_tools
        dynamic_tool_provider.initialize()
        
        results = dynamic_tool_provider.search_tools("", tags=["test"])
        
        assert "tagged_tool" in results
    
    def test_tool_provider_search_tools_multiple_filters(self, static_tool_provider):
        """Test tool search with multiple filters."""
        static_tool_provider.initialize()
        
        results = static_tool_provider.search_tools("built", category="Built-in")
        
        assert len(results) >= 1
        for tool in results.values():
            assert tool.category == "Built-in"
            assert "built" in tool.name.lower() or "built" in tool.tool_id.lower()
    
    def test_tool_provider_search_tools_no_matches(self, static_tool_provider):
        """Test tool search with no matches."""
        static_tool_provider.initialize()
        
        results = static_tool_provider.search_tools("nonexistent_search_term")
        
        assert results == {}
    
    def test_tool_provider_case_insensitive_search(self, static_tool_provider):
        """Test case insensitive search."""
        static_tool_provider.initialize()
        
        results_lower = static_tool_provider.search_tools("built")
        results_upper = static_tool_provider.search_tools("BUILT")
        results_mixed = static_tool_provider.search_tools("BuilT")
        
        assert results_lower == results_upper == results_mixed
        assert len(results_lower) >= 1


class TestToolProviderIntegration:
    """Integration tests for ToolProvider classes."""
    
    def test_static_and_dynamic_provider_integration(self, static_tools_config, sample_tool_metadata):
        """Test integration between static and dynamic providers."""
        # Create both providers
        static_provider = StaticToolProvider(tools_config=static_tools_config)
        
        mock_library_manager = Mock()
        mock_library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_provider = DynamicToolProvider(library_manager=mock_library_manager)
        
        # Initialize both
        static_provider.initialize()
        dynamic_provider.initialize()
        
        # Get tools from both
        static_tools = static_provider.get_tools()
        dynamic_tools = dynamic_provider.get_tools()
        
        # Should have different tools
        assert len(static_tools) >= 2
        assert len(dynamic_tools) >= 2
        
        # Static tools should be STATIC source, dynamic should be DYNAMIC
        for tool in static_tools.values():
            assert tool.source == ToolSource.STATIC
            assert tool.status == ToolStatus.INSTALLED
            assert tool.trusted is True
        
        for tool in dynamic_tools.values():
            assert tool.source == ToolSource.DYNAMIC
    
    def test_provider_info_consistency(self, static_tool_provider, dynamic_tool_provider, sample_tool_metadata):
        """Test that provider info is consistent."""
        # Initialize providers
        static_tool_provider.initialize()
        
        dynamic_tool_provider.library_manager.get_available_tools.return_value = sample_tool_metadata['tools']
        dynamic_tool_provider.initialize()
        
        # Get provider info
        static_info = static_tool_provider.get_provider_info()
        dynamic_info = dynamic_tool_provider.get_provider_info()
        
        # Check required fields
        for info in [static_info, dynamic_info]:
            assert 'provider_id' in info
            assert 'provider_name' in info
            assert 'initialized' in info
            assert 'total_tools' in info
            assert 'categories' in info
            assert 'source_type' in info
        
        # Check specific values
        assert static_info['provider_id'] == "static"
        assert dynamic_info['provider_id'] == "dynamic"
        assert static_info['initialized'] is True
        assert dynamic_info['initialized'] is True


@pytest.mark.integration
class TestToolProviderEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_tool_info_from_dict_with_missing_data(self):
        """Test ToolInfo.from_dict with minimal data."""
        minimal_data = {}
        
        tool = ToolInfo.from_dict(minimal_data)
        
        # Should create with defaults
        assert tool.tool_id == ""
        assert tool.name == ""
        assert tool.version == "1.0.0"
        assert tool.source == ToolSource.DYNAMIC
        assert tool.status == ToolStatus.AVAILABLE
    
    def test_tool_provider_with_corrupted_data(self, dynamic_tool_provider):
        """Test provider handling of corrupted tool data."""
        corrupted_data = {
            "corrupted_tool": {
                "id": None,
                "name": 12345,  # Should be string
                "description": ["not", "a", "string"],
                "version": {"major": 1},  # Should be string
                "tags": "not_a_list"  # Should be list
            }
        }
        
        dynamic_tool_provider.library_manager.get_available_tools.return_value = corrupted_data
        
        # Should handle gracefully and not crash
        result = dynamic_tool_provider.initialize()
        assert result is True
    
    def test_platform_compatibility_edge_cases(self):
        """Test platform compatibility with edge cases."""
        tool = ToolInfo(
            tool_id="edge_case_tool",
            name="Edge Case Tool",
            platform_support=[]  # Empty list
        )
        
        # Empty platform support should not match anything
        assert tool.is_compatible_platform('windows') is False
        assert tool.is_compatible_platform('linux') is False
        
        # Test with unknown platform
        tool2 = ToolInfo(
            tool_id="unknown_platform_tool",
            name="Unknown Platform Tool",
            platform_support=["unknown_os"]
        )
        
        assert tool2.is_compatible_platform('windows') is False
        assert tool2.is_compatible_platform('unknown_os') is True