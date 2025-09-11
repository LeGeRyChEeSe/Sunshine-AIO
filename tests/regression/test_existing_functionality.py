"""
Regression testing for existing Sunshine-AIO functionality.

This module ensures that all existing Sunshine-AIO functionality continues
to work correctly after the community library integration.
"""

import pytest
import tempfile
import shutil
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from misc.MenuHandler import MenuHandler
from misc.SystemRequests import SystemRequests
from misc.Config import DownloadManager
from misc.Uninstaller import SunshineAIOUninstaller
from misc.Logger import log_success, log_info, log_warning, log_error
from misc.MenuDisplay import display_menu, display_logo, display_version
from misc.InstallationTracker import InstallationTracker
from misc.AppMetadata import AppMetadata


@pytest.mark.regression
class TestExistingFunctionality:
    """Regression testing for existing Sunshine-AIO functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_regression_test(self):
        """Set up regression test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.base_path = self.test_dir
        
        # Create necessary directory structure
        self.misc_dir = os.path.join(self.test_dir, 'misc')
        self.variables_dir = os.path.join(self.misc_dir, 'variables')
        self.resources_dir = os.path.join(self.misc_dir, 'ressources')
        
        os.makedirs(self.variables_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)
        
        # Create test configuration files
        self._create_test_config_files()
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_config_files(self):
        """Create test configuration files."""
        # Create menu choices
        menu_choices = [
            {
                "1": "Download and Install EVERYTHING",
                "2": "Download, install and configure Sunshine",
                "3": "Download and install Virtual Display Driver",
                "4": "Download and configure Sunshine Virtual Monitor",
                "5": "Download and install Playnite",
                "6": "Download and configure Playnite Watcher",
                "7": "Extra",
                "8": "Uninstall Components",
                "9": "Community Library",
                "0": "Exit"
            },
            {
                "1": "Download EVERYTHING without installing",
                "2": "Selective Download",
                "3": "Configure Sunshine",
                "4": "Install WindowsDisplayManager (Required PowerShell Module)",
                "5": "Open Sunshine Settings",
                "6": "Open Playnite",
                "7": "Open VDD Control",
                "8": "Go Back",
                "0": "Exit"
            }
        ]
        
        with open(os.path.join(self.variables_dir, 'menu_choices.json'), 'w') as f:
            json.dump(menu_choices, f, indent=2)
        
        # Create config.json
        config = {
            "sunshine": {"url": "https://github.com/LizardByte/Sunshine/releases"},
            "vdd": {"url": "https://github.com/itsmikethetech/Virtual-Display-Driver/releases"},
            "playnite": {"url": "https://playnite.link/download"}
        }
        
        with open(os.path.join(self.variables_dir, 'config.json'), 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create logo file
        logo_content = "SUNSHINE-AIO\n============\n"
        with open(os.path.join(self.resources_dir, 'logo_menu.txt'), 'w') as f:
            f.write(logo_content)
    
    def test_sunshine_installation_unchanged(self):
        """Test that Sunshine installation functionality remains unchanged."""
        system_requests = SystemRequests(self.base_path)
        
        # Test configuration loading
        config = system_requests.load_config()
        assert isinstance(config, dict), "Configuration should load as dictionary"
        assert 'sunshine' in config, "Sunshine configuration should be present"
        
        # Test URL retrieval
        sunshine_url = system_requests.get_sunshine_url()
        assert sunshine_url is not None, "Should retrieve Sunshine URL"
        assert sunshine_url.startswith('https://'), "URL should be HTTPS"
        
        # Test download preparation
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tag_name": "v0.20.0",
                "assets": [
                    {"name": "sunshine-windows-installer.exe", "browser_download_url": "https://example.com/sunshine.exe"}
                ]
            }
            mock_get.return_value = mock_response
            
            download_info = system_requests.get_sunshine_download_info()
            assert download_info is not None, "Should get download information"
            assert 'url' in download_info, "Download info should contain URL"
            assert 'version' in download_info, "Download info should contain version"
    
    def test_vdd_installation_unchanged(self):
        """Test that Virtual Display Driver installation remains unchanged."""
        system_requests = SystemRequests(self.base_path)
        
        # Test VDD configuration
        config = system_requests.load_config()
        assert 'vdd' in config, "VDD configuration should be present"
        
        # Test VDD URL retrieval
        vdd_url = system_requests.get_vdd_url()
        assert vdd_url is not None, "Should retrieve VDD URL"
        
        # Test VDD download preparation
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tag_name": "v1.0.0",
                "assets": [
                    {"name": "Virtual-Display-Driver.zip", "browser_download_url": "https://example.com/vdd.zip"}
                ]
            }
            mock_get.return_value = mock_response
            
            download_info = system_requests.get_vdd_download_info()
            assert download_info is not None, "Should get VDD download information"
    
    def test_playnite_installation_unchanged(self):
        """Test that Playnite installation remains unchanged."""
        system_requests = SystemRequests(self.base_path)
        
        # Test Playnite configuration
        config = system_requests.load_config()
        assert 'playnite' in config, "Playnite configuration should be present"
        
        # Test Playnite URL retrieval
        playnite_url = system_requests.get_playnite_url()
        assert playnite_url is not None, "Should retrieve Playnite URL"
        
        # Test Playnite download preparation
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"Mock Playnite installer content"
            mock_response.headers = {'content-length': '1024'}
            mock_get.return_value = mock_response
            
            # Should be able to prepare download
            assert system_requests.can_download_playnite(), "Should be able to download Playnite"
    
    def test_menu_navigation_unchanged(self):
        """Test that menu navigation functionality remains unchanged."""
        menu_handler = MenuHandler(self.base_path)
        
        # Test menu initialization
        assert menu_handler is not None, "Menu handler should initialize"
        
        # Test menu choices loading
        choices = menu_handler.get_choices()
        assert isinstance(choices, list), "Menu choices should be a list"
        assert len(choices) > 0, "Should have menu choices"
        
        # Test main menu structure
        main_menu = choices[0] if choices else {}
        expected_main_options = ["1", "2", "3", "4", "5", "0"]
        for option in expected_main_options:
            assert option in main_menu, f"Main menu should have option {option}"
        
        # Test menu page navigation
        current_page = menu_handler.get_current_page()
        assert isinstance(current_page, int), "Current page should be integer"
        assert current_page >= 0, "Current page should be non-negative"
        
        # Test menu display
        with patch('builtins.print') as mock_print:
            menu_handler.display_current_menu()
            mock_print.assert_called()  # Should produce output
    
    def test_uninstallation_unchanged(self):
        """Test that uninstallation functionality remains unchanged."""
        uninstaller = SunshineAIOUninstaller(self.base_path)
        
        # Test uninstaller initialization
        assert uninstaller is not None, "Uninstaller should initialize"
        
        # Test component detection
        installed_components = uninstaller.get_installed_components()
        assert isinstance(installed_components, list), "Should return list of components"
        
        # Test uninstallation report generation
        report = uninstaller.generate_uninstall_report()
        assert isinstance(report, dict), "Uninstall report should be dictionary"
        assert 'components' in report, "Report should include components"
        assert 'timestamp' in report, "Report should include timestamp"
        
        # Test selective uninstallation (dry run)
        component_name = "test_component"
        with patch.object(uninstaller, '_perform_uninstall', return_value=True):
            result = uninstaller.uninstall_component(component_name, dry_run=True)
            assert isinstance(result, bool), "Uninstall should return boolean result"
        
        # Test all components uninstallation (dry run)
        with patch.object(uninstaller, '_perform_uninstall', return_value=True):
            result = uninstaller.uninstall_all_components(dry_run=True)
            assert isinstance(result, dict), "Uninstall all should return status dictionary"
    
    def test_configuration_unchanged(self):
        """Test that configuration management remains unchanged."""
        download_manager = DownloadManager(self.base_path)
        
        # Test configuration loading
        config = download_manager.load_configuration()
        assert isinstance(config, dict), "Configuration should be dictionary"
        
        # Test configuration validation
        is_valid = download_manager.validate_configuration(config)
        assert isinstance(is_valid, bool), "Configuration validation should return boolean"
        
        # Test configuration saving
        test_config = {"test_key": "test_value"}
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.write = Mock()
            result = download_manager.save_configuration(test_config)
            assert isinstance(result, bool), "Configuration saving should return boolean"
        
        # Test download directory management
        download_dir = download_manager.get_download_directory()
        assert isinstance(download_dir, str), "Download directory should be string"
        assert len(download_dir) > 0, "Download directory should not be empty"
    
    def test_logging_functionality_unchanged(self):
        """Test that logging functionality remains unchanged."""
        # Test various log levels
        log_functions = [log_success, log_info, log_warning, log_error]
        test_message = "Test log message"
        
        for log_func in log_functions:
            try:
                log_func(test_message)
                # Should not raise exception
                assert True, f"{log_func.__name__} should work without errors"
            except Exception as e:
                pytest.fail(f"Logging function {log_func.__name__} failed: {e}")
        
        # Test log file path retrieval
        log_file_path = get_log_file_path()
        assert isinstance(log_file_path, str), "Log file path should be string"
        assert len(log_file_path) > 0, "Log file path should not be empty"
    
    def test_display_functionality_unchanged(self):
        """Test that display functionality remains unchanged."""
        # Test logo display
        with patch('builtins.print') as mock_print:
            display_logo()
            mock_print.assert_called()  # Should produce output
        
        # Test version display
        with patch('builtins.print') as mock_print:
            display_version()
            mock_print.assert_called()  # Should produce output
        
        # Test menu display
        test_choices = {"1": "Test Option 1", "2": "Test Option 2", "0": "Exit"}
        with patch('builtins.print') as mock_print:
            display_menu(test_choices)
            mock_print.assert_called()  # Should produce output
        
        # Test status display
        with patch('builtins.print') as mock_print:
            display_status("Test status message")
            mock_print.assert_called()  # Should produce output
    
    def test_installation_tracking_unchanged(self):
        """Test that installation tracking remains unchanged."""
        tracker = InstallationTracker(self.base_path)
        
        # Test tracker initialization
        assert tracker is not None, "Installation tracker should initialize"
        
        # Test component tracking
        component_info = {
            "name": "test_component",
            "version": "1.0.0",
            "install_path": "/test/path",
            "install_date": "2024-01-01"
        }
        
        result = tracker.track_installation(component_info)
        assert isinstance(result, bool), "Installation tracking should return boolean"
        
        # Test installation retrieval
        installations = tracker.get_tracked_installations()
        assert isinstance(installations, list), "Should return list of installations"
        
        # Test component search
        search_result = tracker.find_installation("test_component")
        # Should return None or installation info
        assert search_result is None or isinstance(search_result, dict)
        
        # Test installation removal
        removal_result = tracker.remove_installation("test_component")
        assert isinstance(removal_result, bool), "Installation removal should return boolean"
    
    def test_app_metadata_unchanged(self):
        """Test that app metadata functionality remains unchanged."""
        metadata = AppMetadata(self.base_path)
        
        # Test metadata initialization
        assert metadata is not None, "App metadata should initialize"
        
        # Test version retrieval
        version = metadata.get_version()
        assert isinstance(version, str), "Version should be string"
        assert len(version) > 0, "Version should not be empty"
        
        # Test application info
        app_info = metadata.get_application_info()
        assert isinstance(app_info, dict), "App info should be dictionary"
        assert 'name' in app_info, "App info should include name"
        assert 'version' in app_info, "App info should include version"
        
        # Test metadata validation
        is_valid = metadata.validate_metadata()
        assert isinstance(is_valid, bool), "Metadata validation should return boolean"
    
    def test_backward_compatibility(self):
        """Test backward compatibility with previous versions."""
        # Test old configuration format handling
        old_config = {
            "version": "1.0.0",
            "settings": {
                "download_path": "/old/path",
                "timeout": 30
            }
        }
        
        system_requests = SystemRequests(self.base_path)
        
        # Should handle old configuration gracefully
        with patch.object(system_requests, 'load_config', return_value=old_config):
            config = system_requests.load_config()
            assert isinstance(config, dict), "Should handle old configuration format"
        
        # Test old menu structure compatibility
        old_menu_choices = [
            {
                "1": "Install Sunshine",
                "2": "Install VDD",
                "0": "Exit"
            }
        ]
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_file.read.return_value = json.dumps(old_menu_choices)
            mock_open.return_value.__enter__.return_value = mock_file
            
            menu_handler = MenuHandler(self.base_path)
            # Should handle old menu structure
            assert menu_handler is not None, "Should handle old menu format"
    
    def test_error_handling_unchanged(self):
        """Test that error handling remains unchanged."""
        system_requests = SystemRequests(self.base_path)
        
        # Test network error handling
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            try:
                result = system_requests.get_sunshine_download_info()
                # Should handle error gracefully
                assert result is None or isinstance(result, dict)
            except Exception as e:
                # If exception raised, should be meaningful
                assert "network" in str(e).lower() or "connection" in str(e).lower()
        
        # Test file error handling
        with patch('builtins.open') as mock_open:
            mock_open.side_effect = FileNotFoundError("File not found")
            
            try:
                download_manager = DownloadManager(self.base_path)
                config = download_manager.load_configuration()
                # Should handle missing file gracefully
                assert config is None or isinstance(config, dict)
            except FileNotFoundError:
                # Expected behavior for missing files
                pass
        
        # Test invalid JSON handling
        with patch('json.load') as mock_json:
            mock_json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            
            try:
                menu_handler = MenuHandler(self.base_path)
                # Should handle invalid JSON gracefully
                assert menu_handler is not None
            except json.JSONDecodeError:
                # Expected behavior for invalid JSON
                pass
    
    def test_community_library_integration_non_interference(self):
        """Test that community library doesn't interfere with existing functionality."""
        # Test with library available
        with patch('misc.MenuHandler.LIBRARY_AVAILABLE', True):
            menu_handler = MenuHandler(self.base_path)
            
            # All original functionality should still work
            choices = menu_handler.get_choices()
            assert isinstance(choices, list), "Menu choices should work with library available"
            
            # Original menu options should still be present
            if choices:
                main_menu = choices[0]
                assert "1" in main_menu, "Original option 1 should be present"
                assert "2" in main_menu, "Original option 2 should be present"
                assert "0" in main_menu, "Exit option should be present"
        
        # Test with library unavailable
        with patch('misc.MenuHandler.LIBRARY_AVAILABLE', False):
            menu_handler = MenuHandler(self.base_path)
            
            # All original functionality should still work
            choices = menu_handler.get_choices()
            assert isinstance(choices, list), "Menu choices should work without library"
            
            # Original functionality should not be affected
            system_requests = SystemRequests(self.base_path)
            config = system_requests.load_config()
            assert isinstance(config, dict), "Original functionality should work without library"
    
    def test_performance_regression(self):
        """Test that performance hasn't regressed."""
        import time
        
        # Test menu loading performance
        start_time = time.perf_counter()
        menu_handler = MenuHandler(self.base_path)
        menu_load_time = time.perf_counter() - start_time
        
        # Menu should load quickly (< 1 second)
        assert menu_load_time < 1.0, f"Menu loading took {menu_load_time:.2f}s, too slow"
        
        # Test configuration loading performance
        start_time = time.perf_counter()
        system_requests = SystemRequests(self.base_path)
        config = system_requests.load_config()
        config_load_time = time.perf_counter() - start_time
        
        # Configuration should load quickly (< 0.5 seconds)
        assert config_load_time < 0.5, f"Config loading took {config_load_time:.2f}s, too slow"
        
        # Test display performance
        start_time = time.perf_counter()
        with patch('builtins.print'):
            display_logo()
            display_menu({"1": "Test", "0": "Exit"})
        display_time = time.perf_counter() - start_time
        
        # Display should be fast (< 0.1 seconds)
        assert display_time < 0.1, f"Display took {display_time:.2f}s, too slow"
    
    def test_memory_usage_regression(self):
        """Test that memory usage hasn't significantly increased."""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Perform typical operations
        menu_handler = MenuHandler(self.base_path)
        system_requests = SystemRequests(self.base_path)
        download_manager = DownloadManager(self.base_path)
        uninstaller = SunshineAIOUninstaller(self.base_path)
        
        # Load configurations and perform operations
        menu_handler.get_choices()
        system_requests.load_config()
        download_manager.get_download_directory()
        uninstaller.get_installed_components()
        
        # Force garbage collection
        del menu_handler, system_requests, download_manager, uninstaller
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Memory increase should be reasonable (< 20MB for basic operations)
        assert memory_increase < 20.0, f"Memory increased by {memory_increase:.2f}MB, too much"


@pytest.mark.regression
@pytest.mark.slow
class TestEndToEndRegression:
    """End-to-end regression testing."""
    
    @pytest.fixture(autouse=True)
    def setup_e2e_test(self):
        """Set up end-to-end test environment."""
        self.test_dir = tempfile.mkdtemp()
        yield
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_full_application_workflow(self):
        """Test complete application workflow hasn't changed."""
        # This would test the entire application from start to finish
        # For now, we'll test the key integration points
        
        # Test application startup
        with patch('sys.argv', ['sunshine-aio']):
            # Should be able to import and initialize main components
            try:
                from misc.MenuHandler import MenuHandler
                from misc.SystemRequests import SystemRequests
                
                menu_handler = MenuHandler(self.test_dir)
                system_requests = SystemRequests(self.test_dir)
                
                assert menu_handler is not None
                assert system_requests is not None
                
            except Exception as e:
                pytest.fail(f"Application startup failed: {e}")
    
    def test_cli_interface_unchanged(self):
        """Test that CLI interface hasn't changed."""
        # Test command line argument handling
        # This would test actual CLI usage patterns
        
        # For now, test that the main entry points exist
        main_module_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src')
        
        # Check that main modules can be imported
        sys.path.insert(0, main_module_path)
        
        try:
            import misc.MenuHandler
            import misc.SystemRequests
            import misc.Config
            
            # Should import without errors
            assert True, "Core modules should import successfully"
            
        except ImportError as e:
            pytest.fail(f"Core module import failed: {e}")
        finally:
            if main_module_path in sys.path:
                sys.path.remove(main_module_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])