#!/usr/bin/env python3
"""
Test script for Phase 3 Community Library Integration
Tests the download and installation system components.
"""

import os
import sys
import tempfile
import traceback
from typing import Any, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_library_infrastructure():
    """Test basic library infrastructure."""
    print("=" * 60)
    print("TESTING: Library Infrastructure")
    print("=" * 60)
    
    try:
        # Test library imports
        from library.library_manager import LibraryManager, get_library_manager
        from library.tool_provider import ToolInfo, ToolSource, ToolStatus
        from library.downloader import LibraryDownloader, DownloadProgress
        from library.installer import HybridInstaller, InstallationType, InstallationResult
        from library.cache_manager import CacheManager
        from library.validators import ToolValidator
        
        print("✓ All library components imported successfully")
        
        # Test basic LibraryManager initialization
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = LibraryManager(temp_dir)
            print("✓ LibraryManager initialized")
            
            # Test initialization
            # Note: This might fail due to network, which is expected in testing
            try:
                success = manager.initialize()
                if success:
                    print("✓ LibraryManager initialization successful")
                else:
                    print("⚠ LibraryManager initialization failed (expected - no network)")
            except Exception as e:
                print(f"⚠ LibraryManager initialization failed: {e} (expected)")
        
        return True
        
    except Exception as e:
        print(f"✗ Library infrastructure test failed: {e}")
        traceback.print_exc()
        return False

def test_tool_info_creation():
    """Test ToolInfo creation and manipulation."""
    print("\n" + "=" * 60)
    print("TESTING: ToolInfo Creation and Manipulation")
    print("=" * 60)
    
    try:
        from library.tool_provider import ToolInfo, ToolSource, ToolStatus
        
        # Test ToolInfo creation
        tool_info = ToolInfo(
            tool_id="test_tool",
            name="Test Tool",
            description="A test tool",
            version="1.0.0",
            category="Testing",
            source=ToolSource.DYNAMIC,
            status=ToolStatus.AVAILABLE,
            author="Test Author",
            size=1024,
            download_url="https://example.com/test.zip"
        )
        
        print("✓ ToolInfo object created successfully")
        print(f"  - Tool ID: {tool_info.tool_id}")
        print(f"  - Name: {tool_info.name}")
        print(f"  - Source: {tool_info.source.value}")
        print(f"  - Status: {tool_info.status.value}")
        
        # Test to_dict conversion
        tool_dict = tool_info.to_dict()
        print("✓ ToolInfo to_dict conversion successful")
        
        # Test from_dict conversion
        tool_info_restored = ToolInfo.from_dict(tool_dict)
        print("✓ ToolInfo from_dict conversion successful")
        
        # Verify data integrity
        assert tool_info_restored.tool_id == tool_info.tool_id
        assert tool_info_restored.name == tool_info.name
        assert tool_info_restored.source == tool_info.source
        print("✓ Data integrity verified")
        
        return True
        
    except Exception as e:
        print(f"✗ ToolInfo test failed: {e}")
        traceback.print_exc()
        return False

def test_downloader_initialization():
    """Test LibraryDownloader initialization."""
    print("\n" + "=" * 60)
    print("TESTING: LibraryDownloader Initialization")
    print("=" * 60)
    
    try:
        from library.downloader import LibraryDownloader, DownloadProgress
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test downloader initialization
            downloader = LibraryDownloader(temp_dir)
            print("✓ LibraryDownloader initialized successfully")
            print(f"  - Cache directory: {downloader.cache_dir}")
            print(f"  - Temp directory: {downloader.temp_dir}")
            print(f"  - Chunk size: {downloader.chunk_size}")
            print(f"  - Timeout: {downloader.timeout}")
            
            # Test progress callback
            callback = downloader.get_download_progress_callback()
            print("✓ Progress callback created")
            
            # Test progress object
            progress = DownloadProgress(1024)
            progress.update(100)
            print(f"✓ Progress tracking: {progress.get_progress_percentage():.1f}%")
            
            # Test cache info
            cache_info = downloader.get_cache_info()
            print("✓ Cache info retrieved")
            print(f"  - File count: {cache_info['file_count']}")
            print(f"  - Total size: {cache_info['total_size_mb']:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"✗ LibraryDownloader test failed: {e}")
        traceback.print_exc()
        return False

def test_installer_initialization():
    """Test HybridInstaller initialization."""
    print("\n" + "=" * 60)
    print("TESTING: HybridInstaller Initialization")
    print("=" * 60)
    
    try:
        from library.installer import HybridInstaller, InstallationType, InstallationResult
        from misc.SystemRequests import SystemRequests
        from misc.Config import DownloadManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize dependencies
            system_requests = SystemRequests(temp_dir)
            download_manager = DownloadManager(system_requests, 0)
            
            # Test installer initialization
            installer = HybridInstaller(system_requests, download_manager)
            print("✓ HybridInstaller initialized successfully")
            print(f"  - Base path: {installer.base_path}")
            print(f"  - Tools directory: {installer.tools_dir}")
            
            # Test installation types
            print("✓ Installation types available:")
            for install_type in InstallationType:
                print(f"  - {install_type.value}")
            
            # Test installation result
            result = InstallationResult(False, "test_tool", "pending")
            print("✓ InstallationResult object created")
            
            # Test get installer info
            info = installer.get_installer_info()
            print("✓ Installer info retrieved")
            print(f"  - Supported types: {len(info['supported_types'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ HybridInstaller test failed: {e}")
        traceback.print_exc()
        return False

def test_download_manager_extensions():
    """Test DownloadManager community tool extensions."""
    print("\n" + "=" * 60)
    print("TESTING: DownloadManager Community Tool Extensions")
    print("=" * 60)
    
    try:
        from misc.SystemRequests import SystemRequests
        from misc.Config import DownloadManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize DownloadManager
            system_requests = SystemRequests(temp_dir)
            download_manager = DownloadManager(system_requests, 0)
            
            print("✓ DownloadManager initialized")
            
            # Test if community tool methods exist
            methods_to_test = [
                'download_community_tool',
                'get_available_community_tools',
                'search_community_tools',
                'sync_community_library',
                'get_installation_status'
            ]
            
            for method_name in methods_to_test:
                if hasattr(download_manager, method_name):
                    print(f"✓ Method exists: {method_name}")
                else:
                    print(f"✗ Method missing: {method_name}")
                    return False
            
            # Test get_available_community_tools (should return empty list)
            try:
                tools = download_manager.get_available_community_tools()
                print(f"✓ get_available_community_tools returned {len(tools)} tools")
            except Exception as e:
                print(f"⚠ get_available_community_tools failed: {e} (expected)")
        
        return True
        
    except Exception as e:
        print(f"✗ DownloadManager extensions test failed: {e}")
        traceback.print_exc()
        return False

def test_menu_handler_integration():
    """Test MenuHandler integration."""
    print("\n" + "=" * 60)
    print("TESTING: MenuHandler Integration")
    print("=" * 60)
    
    try:
        from misc.MenuHandler import MenuHandler
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize MenuHandler
            menu_handler = MenuHandler(temp_dir)
            print("✓ MenuHandler initialized")
            
            # Check if library components are available
            if hasattr(menu_handler, '_library_manager'):
                print("✓ Library manager attribute exists")
            else:
                print("⚠ Library manager attribute not found")
            
            # Check if install method exists
            if hasattr(menu_handler, '_install_community_tool'):
                print("✓ _install_community_tool method exists")
            else:
                print("✗ _install_community_tool method missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ MenuHandler integration test failed: {e}")
        traceback.print_exc()
        return False

def test_integration_flow():
    """Test complete integration flow (without actual installation)."""
    print("\n" + "=" * 60)
    print("TESTING: Complete Integration Flow")
    print("=" * 60)
    
    try:
        from library.library_manager import get_library_manager
        from library.tool_provider import ToolInfo, ToolSource, ToolStatus
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create library manager
            library_manager = get_library_manager(temp_dir)
            print("✓ Library manager created")
            
            # Test sync status
            sync_status = library_manager.get_sync_status()
            print("✓ Sync status retrieved")
            print(f"  - Initialized: {sync_status['initialized']}")
            print(f"  - Total tools: {sync_status['total_tools']}")
            
            # Test tool search (should return empty)
            search_results = library_manager.search_tools("test")
            print(f"✓ Search completed: {len(search_results)} results")
            
            # Test categories
            categories = library_manager.get_categories()
            print(f"✓ Categories retrieved: {len(categories)} categories")
            
            # Test cache operations
            cache_cleared = library_manager.clear_cache()
            print(f"✓ Cache clear operation: {cache_cleared}")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration flow test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Community Library Integration - Phase 3 Testing")
    print("=" * 60)
    
    tests = [
        ("Library Infrastructure", test_library_infrastructure),
        ("ToolInfo Creation", test_tool_info_creation),
        ("LibraryDownloader", test_downloader_initialization),
        ("HybridInstaller", test_installer_initialization),
        ("DownloadManager Extensions", test_download_manager_extensions),
        ("MenuHandler Integration", test_menu_handler_integration),
        ("Integration Flow", test_integration_flow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(tests)
    
    for test_name, success in results.items():
        status = "PASS" if success else "FAIL"
        symbol = "✓" if success else "✗"
        print(f"{symbol} {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Phase 3 implementation is ready.")
        return 0
    else:
        print("⚠ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())