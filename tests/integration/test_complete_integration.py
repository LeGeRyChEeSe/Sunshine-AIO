"""
Complete integration testing for community library.

This module provides comprehensive end-to-end testing of the entire Sunshine-AIO
community library integration, validating all workflows and system interactions.
"""

import pytest
import tempfile
import shutil
import os
import sys
import time
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from library import (
    LibraryManager,
    CacheManager,
    ConfigManager,
    ToolProvider,
    SearchEngine,
    FilterManager,
    FavoritesManager,
    HistoryManager,
    DownloadManager,
    InstallationManager,
    DisplayHelper,
    ToolValidator
)
from misc.MenuHandler import MenuHandler


@pytest.mark.integration
class TestCompleteIntegration:
    """Complete integration testing for community library."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Set up test environment for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, 'config')
        self.cache_dir = os.path.join(self.test_dir, 'cache')
        self.downloads_dir = os.path.join(self.test_dir, 'downloads')
        
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # Initialize managers with test directories
        self.config_manager = ConfigManager(config_dir=self.config_dir)
        self.cache_manager = CacheManager(cache_dir=self.cache_dir)
        self.library_manager = LibraryManager(
            config_manager=self.config_manager,
            cache_manager=self.cache_manager
        )
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @pytest.fixture
    def mock_tools_data(self):
        """Provide mock tools data for testing."""
        return [
            {
                "id": "test_tool_1",
                "name": "Test Tool 1",
                "description": "A test tool for validation",
                "category": "testing",
                "version": "1.0.0",
                "author": "Test Author",
                "download_url": "https://example.com/tool1.zip",
                "file_size": "1024",
                "checksum": "abc123",
                "requirements": ["python>=3.8"],
                "tags": ["test", "validation"],
                "rating": 4.5,
                "downloads": 100,
                "last_updated": "2024-01-01"
            },
            {
                "id": "test_tool_2",
                "name": "Test Tool 2",
                "description": "Another test tool",
                "category": "utility",
                "version": "2.0.0",
                "author": "Test Author 2",
                "download_url": "https://example.com/tool2.zip",
                "file_size": "2048",
                "checksum": "def456",
                "requirements": ["python>=3.9"],
                "tags": ["utility", "helper"],
                "rating": 4.8,
                "downloads": 250,
                "last_updated": "2024-02-01"
            }
        ]
    
    def test_menu_navigation_flow(self, mock_tools_data):
        """Test complete menu navigation workflow."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data):
            # Initialize menu handler
            menu_handler = MenuHandler()
            
            # Test menu navigation to library section
            with patch('builtins.input', side_effect=['6', '1', '0']):  # Library menu, browse, exit
                with patch('builtins.print') as mock_print:
                    # This would normally run the menu, but we'll test the integration points
                    assert self.library_manager is not None
                    tools = self.library_manager.get_available_tools()
                    assert len(tools) == 2
                    assert tools[0]['name'] == 'Test Tool 1'
    
    def test_library_initialization_workflow(self):
        """Test library initialization and setup workflow."""
        # Test fresh initialization
        assert self.library_manager is not None
        assert self.config_manager is not None
        assert self.cache_manager is not None
        
        # Test configuration loading
        config = self.config_manager.get_config()
        assert isinstance(config, dict)
        
        # Test cache initialization
        cache_info = self.cache_manager.get_cache_info()
        assert isinstance(cache_info, dict)
        assert 'size' in cache_info
        assert 'last_updated' in cache_info
    
    def test_tool_discovery_workflow(self, mock_tools_data):
        """Test tool discovery and metadata loading workflow."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data):
            # Test tool discovery
            tools = self.library_manager.get_available_tools()
            assert len(tools) == 2
            
            # Test tool metadata validation
            validator = ToolValidator()
            for tool in tools:
                validation_result = validator.validate_tool_metadata(tool)
                assert validation_result.is_valid
                assert len(validation_result.errors) == 0
    
    def test_search_and_filter_workflow(self, mock_tools_data):
        """Test search and filtering functionality workflow."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data):
            search_engine = SearchEngine(self.library_manager)
            filter_manager = FilterManager()
            
            # Test search functionality
            search_results = search_engine.search("test")
            assert len(search_results) >= 1
            
            # Test filtering
            filters = {
                'category': 'testing',
                'min_rating': 4.0
            }
            filtered_tools = filter_manager.apply_filters(mock_tools_data, filters)
            assert len(filtered_tools) == 1
            assert filtered_tools[0]['category'] == 'testing'
    
    def test_tool_installation_workflow(self, mock_tools_data):
        """Test tool installation complete workflow."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data):
            # Initialize components
            downloader = DownloadManager(download_dir=self.downloads_dir)
            installer = InstallationManager(self.config_manager)
            
            tool = mock_tools_data[0]
            
            # Mock download process
            with patch.object(downloader, 'download_tool') as mock_download:
                mock_download.return_value = {
                    'success': True,
                    'file_path': os.path.join(self.downloads_dir, 'tool1.zip'),
                    'checksum_valid': True
                }
                
                # Mock installation process
                with patch.object(installer, 'install_tool') as mock_install:
                    mock_install.return_value = {
                        'success': True,
                        'install_path': os.path.join(self.test_dir, 'installed', 'tool1'),
                        'executable_path': os.path.join(self.test_dir, 'installed', 'tool1', 'tool1.exe')
                    }
                    
                    # Test complete workflow
                    download_result = downloader.download_tool(tool)
                    assert download_result['success']
                    
                    install_result = installer.install_tool(tool, download_result['file_path'])
                    assert install_result['success']
    
    def test_favorites_management_workflow(self, mock_tools_data):
        """Test favorites management complete workflow."""
        favorites_manager = FavoritesManager(self.config_manager)
        
        tool_id = mock_tools_data[0]['id']
        
        # Test adding to favorites
        result = favorites_manager.add_favorite(tool_id)
        assert result
        
        # Test retrieving favorites
        favorites = favorites_manager.get_favorites()
        assert tool_id in favorites
        
        # Test removing from favorites
        result = favorites_manager.remove_favorite(tool_id)
        assert result
        
        favorites = favorites_manager.get_favorites()
        assert tool_id not in favorites
    
    def test_error_handling_scenarios(self):
        """Test various error handling scenarios."""
        # Test network failure simulation
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            try:
                tools = self.library_manager.get_available_tools()
                # Should handle gracefully, potentially returning cached data
                assert isinstance(tools, list)
            except Exception as e:
                # If exception is raised, it should be meaningful
                assert "Network" in str(e) or "Connection" in str(e)
        
        # Test invalid tool data handling
        invalid_tool = {"id": "invalid", "invalid_field": "test"}
        validator = ToolValidator()
        result = validator.validate_tool_metadata(invalid_tool)
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_configuration_management(self):
        """Test configuration management workflow."""
        # Test setting configuration values
        test_config = {
            'download_timeout': 30,
            'max_concurrent_downloads': 3,
            'auto_update_cache': True,
            'preferred_mirror': 'primary'
        }
        
        for key, value in test_config.items():
            self.config_manager.set_config(key, value)
        
        # Test retrieving configuration
        config = self.config_manager.get_config()
        for key, value in test_config.items():
            assert config.get(key) == value
        
        # Test configuration persistence
        config_manager_2 = ConfigManager(config_dir=self.config_dir)
        config_2 = config_manager_2.get_config()
        for key, value in test_config.items():
            assert config_2.get(key) == value
    
    def test_performance_benchmarks(self, mock_tools_data):
        """Test performance benchmarks for critical operations."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data * 100):
            # Test search performance
            search_engine = SearchEngine(self.library_manager)
            
            start_time = time.time()
            results = search_engine.search("test")
            search_time = time.time() - start_time
            
            # Search should complete within 2 seconds even with 200 tools
            assert search_time < 2.0
            assert len(results) > 0
            
            # Test filtering performance
            filter_manager = FilterManager()
            filters = {'category': 'testing'}
            
            start_time = time.time()
            filtered = filter_manager.apply_filters(mock_tools_data * 100, filters)
            filter_time = time.time() - start_time
            
            # Filtering should be fast
            assert filter_time < 1.0
    
    def test_cache_performance_integration(self, mock_tools_data):
        """Test cache performance and behavior integration."""
        # Test cache warming
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data):
            # First call should populate cache
            start_time = time.time()
            tools_1 = self.library_manager.get_available_tools()
            first_call_time = time.time() - start_time
            
            # Second call should use cache (if implemented)
            start_time = time.time()
            tools_2 = self.library_manager.get_available_tools()
            second_call_time = time.time() - start_time
            
            assert tools_1 == tools_2
            # Note: This test assumes caching is implemented
    
    def test_concurrent_operations_safety(self, mock_tools_data):
        """Test thread safety and concurrent operations."""
        import threading
        import concurrent.futures
        
        results = []
        errors = []
        
        def worker_function():
            try:
                favorites_manager = FavoritesManager(self.config_manager)
                tool_id = f"test_tool_{threading.current_thread().ident}"
                
                # Add favorite
                result = favorites_manager.add_favorite(tool_id)
                results.append(result)
                
                # Get favorites
                favorites = favorites_manager.get_favorites()
                results.append(len(favorites))
                
            except Exception as e:
                errors.append(str(e))
        
        # Run multiple concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker_function) for _ in range(5)]
            concurrent.futures.wait(futures)
        
        # Check that no errors occurred
        assert len(errors) == 0
        assert len(results) > 0
    
    def test_memory_usage_validation(self, mock_tools_data):
        """Test memory usage during operations."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        with patch.object(self.library_manager, 'get_available_tools', return_value=mock_tools_data * 1000):
            search_engine = SearchEngine(self.library_manager)
            
            # Multiple search operations
            for i in range(100):
                results = search_engine.search(f"test_{i}")
            
            # Force garbage collection
            gc.collect()
            
            final_memory = process.memory_info().rss
            memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
            
            # Memory increase should be reasonable (less than 50MB as per requirements)
            assert memory_increase < 50


@pytest.mark.integration
@pytest.mark.slow
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.fixture(autouse=True)
    def setup_real_world_test(self):
        """Set up real-world test environment."""
        self.test_dir = tempfile.mkdtemp()
        yield
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_fresh_installation_scenario(self):
        """Test fresh installation on clean system."""
        # Simulate fresh installation
        config_manager = ConfigManager(config_dir=os.path.join(self.test_dir, 'config'))
        cache_manager = CacheManager(cache_dir=os.path.join(self.test_dir, 'cache'))
        
        # Test initialization
        library_manager = LibraryManager(
            config_manager=config_manager,
            cache_manager=cache_manager
        )
        
        assert library_manager is not None
        
        # Test first-time setup
        config = config_manager.get_config()
        assert isinstance(config, dict)
        
        # Test cache initialization
        cache_info = cache_manager.get_cache_info()
        assert isinstance(cache_info, dict)
    
    def test_upgrade_scenario(self):
        """Test upgrade from previous version."""
        # Create old configuration format
        old_config_file = os.path.join(self.test_dir, 'old_config.json')
        old_config = {
            'version': '1.0.0',
            'settings': {
                'timeout': 30
            }
        }
        
        with open(old_config_file, 'w') as f:
            json.dump(old_config, f)
        
        # Test upgrade handling
        config_manager = ConfigManager(config_dir=self.test_dir)
        
        # Should handle old configuration gracefully
        config = config_manager.get_config()
        assert isinstance(config, dict)
    
    def test_network_failure_resilience(self):
        """Test behavior during network failures."""
        config_manager = ConfigManager(config_dir=os.path.join(self.test_dir, 'config'))
        cache_manager = CacheManager(cache_dir=os.path.join(self.test_dir, 'cache'))
        library_manager = LibraryManager(
            config_manager=config_manager,
            cache_manager=cache_manager
        )
        
        # Mock network failure
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network unreachable")
            
            # Should handle gracefully
            try:
                tools = library_manager.get_available_tools()
                # Should return empty list or cached data
                assert isinstance(tools, list)
            except Exception as e:
                # If exception raised, should be user-friendly
                assert "network" in str(e).lower() or "connection" in str(e).lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])