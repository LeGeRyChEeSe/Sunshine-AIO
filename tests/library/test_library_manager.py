"""
Comprehensive unit tests for LibraryManager.

Tests cover initialization, configuration loading, repository metadata fetching,
cache integration, search functionality, and error handling.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import requests

from library.library_manager import LibraryManager, get_library_manager


class TestLibraryManagerInitialization:
    """Test LibraryManager initialization and configuration."""
    
    def test_library_manager_initialization(self, mock_base_path):
        """Test basic LibraryManager initialization."""
        manager = LibraryManager(mock_base_path)
        
        assert manager.base_path == mock_base_path
        assert manager.repository_url == "https://github.com/LeGeRyChEeSe/sunshine-aio-library"
        assert manager.cache_dir == os.path.join(mock_base_path, "cache", "library")
        assert not manager._initialized
        assert manager._tools_cache == {}
        assert manager._last_sync is None
    
    def test_library_manager_initialization_with_custom_params(self, mock_base_path, mock_cache_dir):
        """Test LibraryManager initialization with custom parameters."""
        custom_repo = "https://github.com/custom/repo"
        
        manager = LibraryManager(
            base_path=mock_base_path,
            repository_url=custom_repo,
            cache_dir=mock_cache_dir
        )
        
        assert manager.base_path == mock_base_path
        assert manager.repository_url == custom_repo
        assert manager.cache_dir == mock_cache_dir
    
    def test_cache_directory_creation(self, mock_base_path):
        """Test that cache directory is created during initialization."""
        with patch('os.makedirs') as mock_makedirs:
            manager = LibraryManager(mock_base_path)
            
            expected_cache_dir = os.path.join(mock_base_path, "cache", "library")
            mock_makedirs.assert_called_once_with(expected_cache_dir, exist_ok=True)
    
    def test_cache_directory_creation_failure(self, mock_base_path):
        """Test handling of cache directory creation failure."""
        with patch('os.makedirs', side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                LibraryManager(mock_base_path)
    
    def test_get_library_manager_factory(self, mock_base_path):
        """Test the factory function for LibraryManager."""
        manager = get_library_manager(mock_base_path)
        
        assert isinstance(manager, LibraryManager)
        assert manager.base_path == mock_base_path


class TestLibraryManagerConfiguration:
    """Test LibraryManager configuration and defaults."""
    
    def test_default_configuration(self, library_manager):
        """Test that default configuration is set correctly."""
        config = library_manager.config
        
        assert config['sync_interval'] == 3600
        assert config['validation_enabled'] is True
        assert config['max_retries'] == 3
        assert config['timeout'] == 30
        assert config['user_agent'] == 'Sunshine-AIO/1.0'
    
    def test_sync_status_initial(self, library_manager):
        """Test initial sync status."""
        status = library_manager.get_sync_status()
        
        assert status['initialized'] is False
        assert status['last_sync'] is None
        assert status['cache_dir'] == library_manager.cache_dir
        assert status['repository_url'] == library_manager.repository_url
        assert status['total_tools'] == 0
        assert status['sync_needed'] is True


class TestLibraryManagerInitializeMethod:
    """Test LibraryManager initialize method."""
    
    @patch('library.library_manager.LibraryManager._load_cached_metadata')
    @patch('library.library_manager.LibraryManager.sync_library_metadata')
    def test_initialize_success_with_sync(self, mock_sync, mock_load, library_manager):
        """Test successful initialization with sync."""
        mock_sync.return_value = True
        
        result = library_manager.initialize()
        
        assert result is True
        assert library_manager._initialized is True
        mock_load.assert_called_once()
        mock_sync.assert_called_once()
    
    @patch('library.library_manager.LibraryManager._load_cached_metadata')
    @patch('library.library_manager.LibraryManager.sync_library_metadata')
    def test_initialize_success_no_sync_needed(self, mock_sync, mock_load, library_manager):
        """Test initialization when sync is not needed."""
        library_manager._last_sync = datetime.now()
        mock_sync.return_value = True
        
        result = library_manager.initialize()
        
        assert result is True
        assert library_manager._initialized is True
        mock_load.assert_called_once()
        mock_sync.assert_not_called()
    
    @patch('library.library_manager.LibraryManager._load_cached_metadata')
    @patch('library.library_manager.LibraryManager.sync_library_metadata')
    def test_initialize_sync_failure_continues(self, mock_sync, mock_load, library_manager):
        """Test initialization continues even if sync fails."""
        mock_sync.return_value = False
        
        result = library_manager.initialize()
        
        assert result is True
        assert library_manager._initialized is True
        mock_load.assert_called_once()
        mock_sync.assert_called_once()
    
    @patch('library.library_manager.LibraryManager._load_cached_metadata', side_effect=Exception("Load error"))
    def test_initialize_failure(self, mock_load, library_manager):
        """Test initialization failure handling."""
        result = library_manager.initialize()
        
        assert result is False
        assert library_manager._initialized is False


class TestLibraryManagerSyncFunctionality:
    """Test LibraryManager sync functionality."""
    
    def test_should_sync_no_previous_sync(self, library_manager):
        """Test should_sync when no previous sync."""
        assert library_manager._should_sync() is True
    
    def test_should_sync_recent_sync(self, library_manager):
        """Test should_sync with recent sync."""
        library_manager._last_sync = datetime.now()
        assert library_manager._should_sync() is False
    
    def test_should_sync_old_sync(self, library_manager):
        """Test should_sync with old sync."""
        library_manager._last_sync = datetime.now() - timedelta(seconds=7200)  # 2 hours ago
        assert library_manager._should_sync() is True
    
    @patch('library.library_manager.LibraryManager._fetch_repository_metadata')
    @patch('library.library_manager.LibraryManager._update_cache')
    def test_sync_library_metadata_success(self, mock_update, mock_fetch, library_manager, sample_tool_metadata):
        """Test successful library metadata sync."""
        mock_fetch.return_value = sample_tool_metadata
        
        result = library_manager.sync_library_metadata()
        
        assert result is True
        assert library_manager._last_sync is not None
        mock_fetch.assert_called_once()
        mock_update.assert_called_once_with(sample_tool_metadata)
    
    @patch('library.library_manager.LibraryManager._fetch_repository_metadata')
    def test_sync_library_metadata_fetch_failure(self, mock_fetch, library_manager):
        """Test sync failure when metadata fetch fails."""
        mock_fetch.return_value = None
        
        result = library_manager.sync_library_metadata()
        
        assert result is False
        assert library_manager._last_sync is None
    
    @patch('library.library_manager.LibraryManager._fetch_repository_metadata', side_effect=Exception("Sync error"))
    def test_sync_library_metadata_exception(self, mock_fetch, library_manager):
        """Test sync failure due to exception."""
        result = library_manager.sync_library_metadata()
        
        assert result is False
        assert library_manager._last_sync is None
    
    def test_force_sync(self, library_manager):
        """Test force sync functionality."""
        with patch.object(library_manager, 'sync_library_metadata', return_value=True) as mock_sync:
            result = library_manager.force_sync()
            
            assert result is True
            mock_sync.assert_called_once()


class TestLibraryManagerRepositoryInteraction:
    """Test LibraryManager repository interaction."""
    
    def test_get_repository_api_url_github(self, library_manager):
        """Test GitHub URL conversion to API URL."""
        library_manager.repository_url = "https://github.com/owner/repo"
        
        api_url = library_manager._get_repository_api_url()
        
        assert api_url == "https://api.github.com/repos/owner/repo/contents"
    
    def test_get_repository_api_url_fallback(self, library_manager):
        """Test API URL fallback for non-GitHub URLs."""
        custom_url = "https://api.custom.com/repos/owner/repo"
        library_manager.repository_url = custom_url
        
        api_url = library_manager._get_repository_api_url()
        
        assert api_url == custom_url
    
    @patch('requests.get')
    def test_fetch_repository_metadata_success(self, mock_get, library_manager, mock_github_api_response):
        """Test successful repository metadata fetch."""
        mock_response = Mock()
        mock_response.json.return_value = mock_github_api_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = library_manager._fetch_repository_metadata()
        
        assert result is not None
        assert 'tools' in result
        assert 'repository_info' in result
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_fetch_repository_metadata_network_error(self, mock_get, library_manager):
        """Test repository metadata fetch with network error."""
        mock_get.side_effect = requests.ConnectionError("Connection failed")
        
        result = library_manager._fetch_repository_metadata()
        
        assert result is None
    
    @patch('requests.get')
    def test_fetch_repository_metadata_timeout(self, mock_get, library_manager):
        """Test repository metadata fetch with timeout."""
        mock_get.side_effect = requests.Timeout("Request timed out")
        
        result = library_manager._fetch_repository_metadata()
        
        assert result is None
    
    @patch('requests.get')
    def test_fetch_repository_metadata_json_error(self, mock_get, library_manager):
        """Test repository metadata fetch with JSON decode error."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = library_manager._fetch_repository_metadata()
        
        assert result is None
    
    def test_parse_repository_contents_directories(self, library_manager, mock_github_api_response):
        """Test parsing repository contents with tool directories."""
        result = library_manager._parse_repository_contents(mock_github_api_response)
        
        assert 'tools' in result
        assert 'example_tool' in result['tools']
        assert 'secure_tool' in result['tools']
        assert result['repository_info']['total_tools'] == 2
        
        # Check tool metadata structure
        tool = result['tools']['example_tool']
        assert tool['id'] == 'example_tool'
        assert tool['name'] == 'Example Tool'
        assert tool['category'] == 'General'
    
    def test_parse_repository_contents_empty(self, library_manager):
        """Test parsing empty repository contents."""
        result = library_manager._parse_repository_contents([])
        
        assert result['tools'] == {}
        assert result['repository_info']['total_tools'] == 0
    
    def test_parse_repository_contents_with_metadata_file(self, library_manager):
        """Test parsing repository contents with metadata file."""
        contents = [
            {
                "name": "metadata.json",
                "type": "file",
                "path": "metadata.json",
                "download_url": "https://example.com/metadata.json"
            }
        ]
        
        result = library_manager._parse_repository_contents(contents)
        
        assert 'tools' in result
        # Should still create basic structure even with metadata file


class TestLibraryManagerCacheOperations:
    """Test LibraryManager cache operations."""
    
    @patch('builtins.open')
    @patch('json.dump')
    def test_update_cache_success(self, mock_json_dump, mock_open, library_manager, sample_tool_metadata):
        """Test successful cache update."""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        library_manager._update_cache(sample_tool_metadata)
        
        assert library_manager._tools_cache == sample_tool_metadata
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once_with(sample_tool_metadata, mock_file, indent=2, ensure_ascii=False)
    
    @patch('builtins.open', side_effect=OSError("Write error"))
    def test_update_cache_failure(self, mock_open, library_manager, sample_tool_metadata):
        """Test cache update failure handling."""
        with pytest.raises(OSError):
            library_manager._update_cache(sample_tool_metadata)
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('json.load')
    def test_load_cached_metadata_success(self, mock_json_load, mock_open, mock_exists, library_manager, sample_tool_metadata):
        """Test successful loading of cached metadata."""
        mock_exists.return_value = True
        mock_json_load.return_value = sample_tool_metadata
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        library_manager._load_cached_metadata()
        
        assert library_manager._tools_cache == sample_tool_metadata
        assert library_manager._last_sync is not None
    
    @patch('os.path.exists')
    def test_load_cached_metadata_no_cache(self, mock_exists, library_manager):
        """Test loading when no cache file exists."""
        mock_exists.return_value = False
        
        library_manager._load_cached_metadata()
        
        assert library_manager._tools_cache == {}
        assert library_manager._last_sync is None
    
    @patch('os.path.exists')
    @patch('builtins.open', side_effect=OSError("Read error"))
    def test_load_cached_metadata_error(self, mock_open, mock_exists, library_manager):
        """Test loading cached metadata with read error."""
        mock_exists.return_value = True
        
        library_manager._load_cached_metadata()
        
        assert library_manager._tools_cache == {}
    
    @patch('os.path.exists')
    @patch('os.remove')
    def test_clear_cache_success(self, mock_remove, mock_exists, library_manager):
        """Test successful cache clearing."""
        mock_exists.return_value = True
        library_manager._tools_cache = {"test": "data"}
        library_manager._last_sync = datetime.now()
        
        result = library_manager.clear_cache()
        
        assert result is True
        assert library_manager._tools_cache == {}
        assert library_manager._last_sync is None
        mock_remove.assert_called_once()
    
    @patch('os.path.exists')
    def test_clear_cache_no_file(self, mock_exists, library_manager):
        """Test cache clearing when no cache file exists."""
        mock_exists.return_value = False
        
        result = library_manager.clear_cache()
        
        assert result is True
        assert library_manager._tools_cache == {}
    
    @patch('os.path.exists', side_effect=OSError("Access error"))
    def test_clear_cache_error(self, mock_exists, library_manager):
        """Test cache clearing with error."""
        result = library_manager.clear_cache()
        
        assert result is False


class TestLibraryManagerToolAccess:
    """Test LibraryManager tool access methods."""
    
    def test_get_available_tools_initialized(self, library_manager, sample_tool_metadata):
        """Test getting available tools when initialized."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        tools = library_manager.get_available_tools()
        
        assert tools == sample_tool_metadata['tools']
    
    @patch('library.library_manager.LibraryManager.initialize')
    def test_get_available_tools_not_initialized_success(self, mock_init, library_manager, sample_tool_metadata):
        """Test getting available tools when not initialized but init succeeds."""
        library_manager._initialized = False
        library_manager._tools_cache = sample_tool_metadata
        mock_init.return_value = True
        
        # Simulate initialization setting the flag
        def side_effect():
            library_manager._initialized = True
            return True
        mock_init.side_effect = side_effect
        
        tools = library_manager.get_available_tools()
        
        assert tools == sample_tool_metadata['tools']
        mock_init.assert_called_once()
    
    @patch('library.library_manager.LibraryManager.initialize')
    def test_get_available_tools_initialization_fails(self, mock_init, library_manager):
        """Test getting available tools when initialization fails."""
        library_manager._initialized = False
        mock_init.return_value = False
        
        tools = library_manager.get_available_tools()
        
        assert tools == {}
        mock_init.assert_called_once()
    
    def test_get_tool_info_existing(self, library_manager, sample_tool_metadata):
        """Test getting info for existing tool."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        tool_info = library_manager.get_tool_info("example_tool")
        
        assert tool_info is not None
        assert tool_info['id'] == 'example_tool'
        assert tool_info['name'] == 'Example Tool'
    
    def test_get_tool_info_nonexistent(self, library_manager, sample_tool_metadata):
        """Test getting info for non-existent tool."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        tool_info = library_manager.get_tool_info("nonexistent_tool")
        
        assert tool_info is None
    
    def test_is_tool_available_existing(self, library_manager, sample_tool_metadata):
        """Test checking availability of existing tool."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        available = library_manager.is_tool_available("example_tool")
        
        assert available is True
    
    def test_is_tool_available_nonexistent(self, library_manager, sample_tool_metadata):
        """Test checking availability of non-existent tool."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        available = library_manager.is_tool_available("nonexistent_tool")
        
        assert available is False


class TestLibraryManagerSearchFunctionality:
    """Test LibraryManager search functionality."""
    
    def test_search_tools_by_name(self, library_manager, sample_tool_metadata):
        """Test searching tools by name."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("Example")
        
        assert "example_tool" in results
        assert len(results) == 1
        assert results["example_tool"]["name"] == "Example Tool"
    
    def test_search_tools_by_description(self, library_manager, sample_tool_metadata):
        """Test searching tools by description."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("secure")
        
        assert "secure_tool" in results
        assert results["secure_tool"]["name"] == "Secure Tool"
    
    def test_search_tools_by_id(self, library_manager, sample_tool_metadata):
        """Test searching tools by ID."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("secure_tool")
        
        assert "secure_tool" in results
    
    def test_search_tools_with_category_filter(self, library_manager, sample_tool_metadata):
        """Test searching tools with category filter."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("", category="Security")
        
        assert "secure_tool" in results
        assert "example_tool" not in results
    
    def test_search_tools_no_matches(self, library_manager, sample_tool_metadata):
        """Test searching tools with no matches."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("nonexistent")
        
        assert results == {}
    
    def test_search_tools_case_insensitive(self, library_manager, sample_tool_metadata):
        """Test case insensitive searching."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        results = library_manager.search_tools("EXAMPLE")
        
        assert "example_tool" in results
    
    def test_get_categories(self, library_manager, sample_tool_metadata):
        """Test getting available categories."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        categories = library_manager.get_categories()
        
        assert "Testing" in categories
        assert "Security" in categories
        assert len(categories) >= 2
        assert categories == sorted(categories)  # Should be sorted


class TestLibraryManagerErrorHandling:
    """Test LibraryManager error handling."""
    
    @patch('requests.get')
    def test_network_error_handling(self, mock_get, library_manager):
        """Test handling of network errors during sync."""
        mock_get.side_effect = requests.ConnectionError("Network unreachable")
        
        result = library_manager.sync_library_metadata()
        
        assert result is False
    
    @patch('requests.get')
    def test_timeout_error_handling(self, mock_get, library_manager):
        """Test handling of timeout errors during sync."""
        mock_get.side_effect = requests.Timeout("Request timeout")
        
        result = library_manager.sync_library_metadata()
        
        assert result is False
    
    @patch('requests.get')
    def test_http_error_handling(self, mock_get, library_manager):
        """Test handling of HTTP errors during sync."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = library_manager.sync_library_metadata()
        
        assert result is False


@pytest.mark.integration
class TestLibraryManagerIntegration:
    """Integration tests for LibraryManager."""
    
    def test_full_initialization_workflow(self, mock_base_path, mock_cache_dir):
        """Test complete initialization workflow."""
        with patch('requests.get') as mock_get, \
             patch('os.makedirs'), \
             patch('builtins.open'), \
             patch('json.dump'):
            
            # Mock successful API response
            mock_response = Mock()
            mock_response.json.return_value = []
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            manager = LibraryManager(mock_base_path, cache_dir=mock_cache_dir)
            result = manager.initialize()
            
            assert result is True
            assert manager._initialized is True
    
    def test_search_and_retrieval_workflow(self, library_manager, sample_tool_metadata):
        """Test search and tool retrieval workflow."""
        library_manager._initialized = True
        library_manager._tools_cache = sample_tool_metadata
        
        # Search for tools
        search_results = library_manager.search_tools("tool")
        assert len(search_results) >= 2
        
        # Get specific tool info
        for tool_id in search_results:
            tool_info = library_manager.get_tool_info(tool_id)
            assert tool_info is not None
            assert library_manager.is_tool_available(tool_id) is True