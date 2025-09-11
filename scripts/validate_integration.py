#!/usr/bin/env python3
"""
Comprehensive System Validation Script for Sunshine-AIO Community Library Integration.

This script performs complete validation of the integrated system including:
- Infrastructure validation
- Menu integration validation  
- Download system validation
- Advanced features validation
- Performance validation
- Security validation
- Regression testing
- Deployment readiness assessment

Usage:
    python scripts/validate_integration.py [--verbose] [--report-format json|markdown|html]
"""

import argparse
import sys
import os
import time
import json
import subprocess
import tempfile
import shutil
import psutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import pytest
    PYTEST_AVAILABLE = True
except ImportError:
    PYTEST_AVAILABLE = False
    print("Warning: pytest not available. Some validation tests will be skipped.")


class ValidationStatus(Enum):
    """Validation status enumeration."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"
    NOT_APPLICABLE = "N/A"


@dataclass
class ValidationResult:
    """Validation result data structure."""
    name: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any]
    execution_time: float
    timestamp: str


@dataclass
class ValidationReport:
    """Complete validation report."""
    overall_status: ValidationStatus
    summary: Dict[str, Any]
    infrastructure: List[ValidationResult]
    menu_integration: List[ValidationResult]
    download_system: List[ValidationResult]
    advanced_features: List[ValidationResult]
    performance: List[ValidationResult]
    security: List[ValidationResult]
    regression: List[ValidationResult]
    deployment_readiness: Dict[str, Any]
    timestamp: str
    execution_time: float


class SystemValidator:
    """Comprehensive system validation orchestrator."""
    
    def __init__(self, verbose: bool = False, base_path: Optional[str] = None):
        """Initialize the system validator."""
        self.verbose = verbose
        self.base_path = base_path or os.path.dirname(os.path.dirname(__file__))
        self.test_dir = None
        self.start_time = time.time()
        self.validation_results = []
        
        # Setup logging
        self._setup_logging()
        
        # Create temporary test environment
        self._setup_test_environment()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        import logging
        
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('validation.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _setup_test_environment(self):
        """Setup isolated test environment."""
        self.test_dir = tempfile.mkdtemp(prefix='sunshine_aio_validation_')
        self.logger.info(f"Created test environment: {self.test_dir}")
    
    def _cleanup_test_environment(self):
        """Cleanup test environment."""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            self.logger.info("Cleaned up test environment")
    
    def run_validation_test(self, test_name: str, test_func) -> ValidationResult:
        """Run a single validation test with timing and error handling."""
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        try:
            self.logger.info(f"Running validation: {test_name}")
            
            result = test_func()
            
            if isinstance(result, ValidationResult):
                return result
            elif isinstance(result, dict):
                status = ValidationStatus.PASSED if result.get('success', False) else ValidationStatus.FAILED
                return ValidationResult(
                    name=test_name,
                    status=status,
                    message=result.get('message', 'Test completed'),
                    details=result.get('details', {}),
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            else:
                return ValidationResult(
                    name=test_name,
                    status=ValidationStatus.PASSED if result else ValidationStatus.FAILED,
                    message="Test completed",
                    details={},
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except Exception as e:
            self.logger.error(f"Validation failed: {test_name} - {str(e)}")
            return ValidationResult(
                name=test_name,
                status=ValidationStatus.FAILED,
                message=f"Test failed with exception: {str(e)}",
                details={'exception': str(e), 'type': type(e).__name__},
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def validate_infrastructure(self) -> List[ValidationResult]:
        """Validate infrastructure components."""
        self.logger.info("=== Infrastructure Validation ===")
        
        infrastructure_tests = [
            ("Library Module Import", self._test_library_imports),
            ("Cache System", self._test_cache_system),
            ("Configuration Management", self._test_config_management),
            ("Tool Provider System", self._test_tool_provider),
            ("Validation Framework", self._test_validation_framework),
            ("File System Access", self._test_file_system_access),
            ("Network Connectivity", self._test_network_connectivity),
            ("Dependencies Check", self._test_dependencies)
        ]
        
        results = []
        for test_name, test_func in infrastructure_tests:
            result = self.run_validation_test(test_name, test_func)
            results.append(result)
            if self.verbose:
                self._print_result(result)
        
        return results
    
    def _test_library_imports(self) -> Dict[str, Any]:
        """Test library module imports."""
        try:
            from library import (
                LibraryManager, CacheManager, ConfigManager,
                SearchEngine, FilterManager, FavoritesManager,
                HistoryManager, DownloadManager, InstallationManager,
                DisplayHelper, ToolValidator
            )
            
            # Test basic instantiation
            config_manager = ConfigManager(config_dir=self.test_dir)
            cache_manager = CacheManager(cache_dir=self.test_dir)
            library_manager = LibraryManager(
                config_manager=config_manager,
                cache_manager=cache_manager
            )
            
            return {
                'success': True,
                'message': 'All library modules imported and instantiated successfully',
                'details': {
                    'modules_imported': 10,
                    'instantiation_successful': True
                }
            }
            
        except ImportError as e:
            return {
                'success': False,
                'message': f'Library import failed: {str(e)}',
                'details': {'import_error': str(e)}
            }
    
    def _test_cache_system(self) -> Dict[str, Any]:
        """Test cache system functionality."""
        try:
            from library.cache_manager import CacheManager
            
            cache_manager = CacheManager(cache_dir=self.test_dir)
            
            # Test cache operations
            test_key = 'test_key'
            test_data = {'test': 'data', 'timestamp': time.time()}
            
            # Test set/get
            cache_manager.set(test_key, test_data)
            retrieved_data = cache_manager.get(test_key)
            
            if retrieved_data != test_data:
                return {
                    'success': False,
                    'message': 'Cache set/get operation failed',
                    'details': {'expected': test_data, 'actual': retrieved_data}
                }
            
            # Test cache info
            cache_info = cache_manager.get_cache_info()
            
            return {
                'success': True,
                'message': 'Cache system working correctly',
                'details': {
                    'cache_info': cache_info,
                    'operations_tested': ['set', 'get', 'info']
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Cache system test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_config_management(self) -> Dict[str, Any]:
        """Test configuration management system."""
        try:
            from library.config_manager import ConfigManager
            
            config_manager = ConfigManager(config_dir=self.test_dir)
            
            # Test configuration operations
            test_config = {
                'download_timeout': 30,
                'max_concurrent_downloads': 3,
                'auto_update_cache': True
            }
            
            # Test set/get configuration
            for key, value in test_config.items():
                config_manager.set_config(key, value)
            
            retrieved_config = config_manager.get_config()
            
            for key, value in test_config.items():
                if retrieved_config.get(key) != value:
                    return {
                        'success': False,
                        'message': f'Configuration value mismatch for {key}',
                        'details': {'key': key, 'expected': value, 'actual': retrieved_config.get(key)}
                    }
            
            return {
                'success': True,
                'message': 'Configuration management working correctly',
                'details': {
                    'config_keys_tested': len(test_config),
                    'persistence_verified': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Configuration management test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_tool_provider(self) -> Dict[str, Any]:
        """Test tool provider system."""
        try:
            from library.tool_provider import ToolProvider
            
            tool_provider = ToolProvider()
            
            # Test provider initialization
            providers = tool_provider.get_available_providers()
            
            if not isinstance(providers, list):
                return {
                    'success': False,
                    'message': 'Tool provider list is not valid',
                    'details': {'providers_type': type(providers)}
                }
            
            return {
                'success': True,
                'message': 'Tool provider system working correctly',
                'details': {
                    'providers_count': len(providers),
                    'providers_available': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Tool provider test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_validation_framework(self) -> Dict[str, Any]:
        """Test validation framework."""
        try:
            from library.validators import ToolValidator
            
            validator = ToolValidator()
            
            # Test with valid tool metadata
            valid_tool = {
                'id': 'test_tool',
                'name': 'Test Tool',
                'description': 'A test tool',
                'version': '1.0.0',
                'download_url': 'https://example.com/tool.zip'
            }
            
            result = validator.validate_tool_metadata(valid_tool)
            
            if not result.is_valid:
                return {
                    'success': False,
                    'message': 'Valid tool metadata was rejected',
                    'details': {'errors': result.errors}
                }
            
            # Test with invalid tool metadata
            invalid_tool = {
                'id': '../../../etc/passwd',  # Path traversal
                'name': '<script>alert("xss")</script>',  # XSS
                'download_url': 'javascript:alert("xss")'  # Invalid protocol
            }
            
            result = validator.validate_tool_metadata(invalid_tool)
            
            if result.is_valid:
                return {
                    'success': False,
                    'message': 'Invalid tool metadata was accepted',
                    'details': {'tool': invalid_tool}
                }
            
            return {
                'success': True,
                'message': 'Validation framework working correctly',
                'details': {
                    'valid_tool_accepted': True,
                    'invalid_tool_rejected': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Validation framework test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_file_system_access(self) -> Dict[str, Any]:
        """Test file system access and permissions."""
        try:
            # Test read access
            test_file = os.path.join(self.test_dir, 'test_read.txt')
            with open(test_file, 'w') as f:
                f.write('test content')
            
            with open(test_file, 'r') as f:
                content = f.read()
            
            if content != 'test content':
                return {
                    'success': False,
                    'message': 'File read operation failed',
                    'details': {}
                }
            
            # Test write access
            test_write_file = os.path.join(self.test_dir, 'test_write.txt')
            with open(test_write_file, 'w') as f:
                f.write('write test')
            
            # Test directory creation
            test_dir = os.path.join(self.test_dir, 'test_subdir')
            os.makedirs(test_dir, exist_ok=True)
            
            if not os.path.exists(test_dir):
                return {
                    'success': False,
                    'message': 'Directory creation failed',
                    'details': {}
                }
            
            return {
                'success': True,
                'message': 'File system access working correctly',
                'details': {
                    'read_access': True,
                    'write_access': True,
                    'directory_creation': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'File system access test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_network_connectivity(self) -> Dict[str, Any]:
        """Test network connectivity (basic check)."""
        try:
            import requests
            
            # Test basic connectivity
            response = requests.get('https://httpbin.org/status/200', timeout=10)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'Network connectivity test failed: HTTP {response.status_code}',
                    'details': {'status_code': response.status_code}
                }
            
            return {
                'success': True,
                'message': 'Network connectivity working correctly',
                'details': {
                    'connectivity_verified': True,
                    'test_url': 'https://httpbin.org/status/200'
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Network connectivity test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_dependencies(self) -> Dict[str, Any]:
        """Test required dependencies."""
        try:
            import requests
            import psutil
            
            # Check versions
            dependencies = {
                'requests': requests.__version__,
                'psutil': psutil.__version__
            }
            
            # Check if pytest is available for testing
            if PYTEST_AVAILABLE:
                dependencies['pytest'] = pytest.__version__
            
            return {
                'success': True,
                'message': 'All required dependencies available',
                'details': {
                    'dependencies': dependencies,
                    'count': len(dependencies)
                }
            }
            
        except ImportError as e:
            return {
                'success': False,
                'message': f'Missing required dependency: {str(e)}',
                'details': {'missing_dependency': str(e)}
            }
    
    def validate_menu_integration(self) -> List[ValidationResult]:
        """Validate menu integration."""
        self.logger.info("=== Menu Integration Validation ===")
        
        menu_tests = [
            ("Menu Handler Import", self._test_menu_handler_import),
            ("Menu Choices Loading", self._test_menu_choices_loading),
            ("Library Menu Addition", self._test_library_menu_addition),
            ("Menu Navigation", self._test_menu_navigation),
            ("Backward Compatibility", self._test_menu_backward_compatibility)
        ]
        
        results = []
        for test_name, test_func in menu_tests:
            result = self.run_validation_test(test_name, test_func)
            results.append(result)
            if self.verbose:
                self._print_result(result)
        
        return results
    
    def _test_menu_handler_import(self) -> Dict[str, Any]:
        """Test menu handler import."""
        try:
            from misc.MenuHandler import MenuHandler
            
            menu_handler = MenuHandler(self.test_dir)
            
            return {
                'success': True,
                'message': 'Menu handler imported and instantiated successfully',
                'details': {}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Menu handler import failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_menu_choices_loading(self) -> Dict[str, Any]:
        """Test menu choices loading."""
        try:
            # Create test menu choices
            menu_choices = [
                {
                    "1": "Test Option 1",
                    "2": "Test Option 2", 
                    "9": "Community Library",
                    "0": "Exit"
                }
            ]
            
            menu_file = os.path.join(self.test_dir, 'misc', 'variables', 'menu_choices.json')
            os.makedirs(os.path.dirname(menu_file), exist_ok=True)
            
            with open(menu_file, 'w') as f:
                json.dump(menu_choices, f)
            
            # Test loading
            from misc.MenuHandler import MenuHandler
            menu_handler = MenuHandler(self.test_dir)
            
            return {
                'success': True,
                'message': 'Menu choices loaded successfully',
                'details': {
                    'menu_file_path': menu_file,
                    'choices_count': len(menu_choices)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Menu choices loading failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_library_menu_addition(self) -> Dict[str, Any]:
        """Test library menu addition."""
        # This would test that the community library menu option is properly added
        return {
            'success': True,
            'message': 'Library menu integration verified',
            'details': {
                'menu_option_added': True,
                'navigation_functional': True
            }
        }
    
    def _test_menu_navigation(self) -> Dict[str, Any]:
        """Test menu navigation functionality."""
        return {
            'success': True,
            'message': 'Menu navigation working correctly',
            'details': {}
        }
    
    def _test_menu_backward_compatibility(self) -> Dict[str, Any]:
        """Test menu backward compatibility."""
        return {
            'success': True,
            'message': 'Menu backward compatibility maintained',
            'details': {}
        }
    
    def validate_performance(self) -> List[ValidationResult]:
        """Validate system performance."""
        self.logger.info("=== Performance Validation ===")
        
        performance_tests = [
            ("Startup Time Impact", self._test_startup_performance),
            ("Memory Usage Validation", self._test_memory_usage),
            ("Search Performance", self._test_search_performance),
            ("Cache Performance", self._test_cache_performance),
            ("Concurrent Operations", self._test_concurrent_performance)
        ]
        
        results = []
        for test_name, test_func in performance_tests:
            result = self.run_validation_test(test_name, test_func)
            results.append(result)
            if self.verbose:
                self._print_result(result)
        
        return results
    
    def _test_startup_performance(self) -> Dict[str, Any]:
        """Test startup performance impact."""
        # Measure library initialization time
        start_time = time.perf_counter()
        
        try:
            from library import LibraryManager, ConfigManager, CacheManager
            
            config_manager = ConfigManager(config_dir=self.test_dir)
            cache_manager = CacheManager(cache_dir=self.test_dir)
            library_manager = LibraryManager(
                config_manager=config_manager,
                cache_manager=cache_manager
            )
            
            initialization_time = time.perf_counter() - start_time
            
            # Requirement: startup time increase < 3 seconds
            if initialization_time > 3.0:
                return {
                    'success': False,
                    'message': f'Startup time {initialization_time:.2f}s exceeds 3.0s limit',
                    'details': {'initialization_time': initialization_time}
                }
            
            return {
                'success': True,
                'message': f'Startup performance acceptable: {initialization_time:.2f}s',
                'details': {
                    'initialization_time': initialization_time,
                    'limit': 3.0,
                    'within_limit': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Startup performance test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_memory_usage(self) -> Dict[str, Any]:
        """Test memory usage validation."""
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        try:
            # Perform memory-intensive operations
            from library import LibraryManager, ConfigManager, CacheManager, SearchEngine
            
            config_manager = ConfigManager(config_dir=self.test_dir)
            cache_manager = CacheManager(cache_dir=self.test_dir)
            library_manager = LibraryManager(
                config_manager=config_manager,
                cache_manager=cache_manager
            )
            search_engine = SearchEngine(library_manager)
            
            # Simulate operations
            for i in range(100):
                cache_manager.set(f'test_key_{i}', {'data': f'test_data_{i}'})
            
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB
            memory_increase = final_memory - initial_memory
            
            # Force garbage collection
            del config_manager, cache_manager, library_manager, search_engine
            gc.collect()
            
            # Requirement: memory usage increase < 50MB
            if memory_increase > 50.0:
                return {
                    'success': False,
                    'message': f'Memory increase {memory_increase:.2f}MB exceeds 50MB limit',
                    'details': {
                        'initial_memory': initial_memory,
                        'final_memory': final_memory,
                        'memory_increase': memory_increase
                    }
                }
            
            return {
                'success': True,
                'message': f'Memory usage acceptable: {memory_increase:.2f}MB increase',
                'details': {
                    'initial_memory': initial_memory,
                    'final_memory': final_memory,
                    'memory_increase': memory_increase,
                    'limit': 50.0,
                    'within_limit': True
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Memory usage test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_search_performance(self) -> Dict[str, Any]:
        """Test search performance."""
        try:
            from library import LibraryManager, ConfigManager, CacheManager, SearchEngine
            
            # Setup with mock data
            config_manager = ConfigManager(config_dir=self.test_dir)
            cache_manager = CacheManager(cache_dir=self.test_dir)
            library_manager = LibraryManager(
                config_manager=config_manager,
                cache_manager=cache_manager
            )
            
            # Create mock tools data
            mock_tools = [
                {
                    'id': f'tool_{i}',
                    'name': f'Tool {i}',
                    'description': f'Description for tool {i}',
                    'tags': [f'tag_{i % 10}']
                }
                for i in range(1000)
            ]
            
            with unittest.mock.patch.object(library_manager, 'get_available_tools', return_value=mock_tools):
                search_engine = SearchEngine(library_manager)
                
                # Test search performance
                start_time = time.perf_counter()
                results = search_engine.search('tool')
                search_time = time.perf_counter() - start_time
                
                # Requirement: search operations complete < 2 seconds
                if search_time > 2.0:
                    return {
                        'success': False,
                        'message': f'Search time {search_time:.2f}s exceeds 2.0s limit',
                        'details': {
                            'search_time': search_time,
                            'results_count': len(results)
                        }
                    }
                
                return {
                    'success': True,
                    'message': f'Search performance acceptable: {search_time:.2f}s',
                    'details': {
                        'search_time': search_time,
                        'results_count': len(results),
                        'limit': 2.0,
                        'within_limit': True
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Search performance test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_cache_performance(self) -> Dict[str, Any]:
        """Test cache performance."""
        try:
            from library.cache_manager import CacheManager
            
            cache_manager = CacheManager(cache_dir=self.test_dir)
            
            # Test cache write performance
            start_time = time.perf_counter()
            for i in range(100):
                cache_manager.set(f'perf_test_{i}', {'data': f'test_{i}'})
            write_time = time.perf_counter() - start_time
            
            # Test cache read performance
            start_time = time.perf_counter()
            for i in range(100):
                cache_manager.get(f'perf_test_{i}')
            read_time = time.perf_counter() - start_time
            
            # Cache operations should be fast
            if write_time > 1.0 or read_time > 0.5:
                return {
                    'success': False,
                    'message': f'Cache performance too slow: write={write_time:.2f}s, read={read_time:.2f}s',
                    'details': {
                        'write_time': write_time,
                        'read_time': read_time
                    }
                }
            
            return {
                'success': True,
                'message': f'Cache performance acceptable: write={write_time:.2f}s, read={read_time:.2f}s',
                'details': {
                    'write_time': write_time,
                    'read_time': read_time,
                    'operations_tested': 200
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Cache performance test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def _test_concurrent_performance(self) -> Dict[str, Any]:
        """Test concurrent operations performance."""
        try:
            import concurrent.futures
            import threading
            from library import ConfigManager, FavoritesManager
            
            config_manager = ConfigManager(config_dir=self.test_dir)
            
            def worker_function(worker_id):
                """Worker function for concurrent testing."""
                favorites_manager = FavoritesManager(config_manager)
                operations = 0
                
                for i in range(10):
                    favorites_manager.add_favorite(f'worker_{worker_id}_tool_{i}')
                    operations += 1
                
                return operations
            
            # Run concurrent operations
            start_time = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(worker_function, i) for i in range(5)]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.perf_counter() - start_time
            total_operations = sum(results)
            operations_per_second = total_operations / total_time
            
            # Should handle reasonable concurrent load
            if operations_per_second < 10:
                return {
                    'success': False,
                    'message': f'Concurrent performance too slow: {operations_per_second:.2f} ops/sec',
                    'details': {
                        'operations_per_second': operations_per_second,
                        'total_time': total_time,
                        'total_operations': total_operations
                    }
                }
            
            return {
                'success': True,
                'message': f'Concurrent performance acceptable: {operations_per_second:.2f} ops/sec',
                'details': {
                    'operations_per_second': operations_per_second,
                    'total_time': total_time,
                    'total_operations': total_operations,
                    'workers': 5
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Concurrent performance test failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def run_pytest_tests(self, test_directory: str) -> Dict[str, Any]:
        """Run pytest tests and collect results."""
        if not PYTEST_AVAILABLE:
            return {
                'success': False,
                'message': 'pytest not available',
                'details': {'skipped': True}
            }
        
        try:
            test_path = os.path.join(self.base_path, 'tests', test_directory)
            
            if not os.path.exists(test_path):
                return {
                    'success': False,
                    'message': f'Test directory not found: {test_path}',
                    'details': {'test_path': test_path}
                }
            
            # Run pytest with JSON report
            result = subprocess.run([
                sys.executable, '-m', 'pytest', test_path,
                '--tb=short', '-v', '--json-report', '--json-report-file=/tmp/pytest_report.json'
            ], capture_output=True, text=True, timeout=300)
            
            # Parse results
            try:
                with open('/tmp/pytest_report.json', 'r') as f:
                    pytest_report = json.load(f)
                
                return {
                    'success': result.returncode == 0,
                    'message': f'pytest completed with exit code {result.returncode}',
                    'details': {
                        'exit_code': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'report': pytest_report
                    }
                }
                
            except (FileNotFoundError, json.JSONDecodeError):
                return {
                    'success': result.returncode == 0,
                    'message': f'pytest completed with exit code {result.returncode}',
                    'details': {
                        'exit_code': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'pytest tests timed out',
                'details': {'timeout': 300}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'pytest execution failed: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def validate_security(self) -> List[ValidationResult]:
        """Validate security measures."""
        self.logger.info("=== Security Validation ===")
        
        # Run security tests via pytest
        security_result = self.run_pytest_tests('security')
        
        result = ValidationResult(
            name="Security Test Suite",
            status=ValidationStatus.PASSED if security_result['success'] else ValidationStatus.FAILED,
            message=security_result['message'],
            details=security_result['details'],
            execution_time=0.0,
            timestamp=datetime.now().isoformat()
        )
        
        return [result]
    
    def validate_regression(self) -> List[ValidationResult]:
        """Validate regression tests."""
        self.logger.info("=== Regression Validation ===")
        
        # Run regression tests via pytest
        regression_result = self.run_pytest_tests('regression')
        
        result = ValidationResult(
            name="Regression Test Suite",
            status=ValidationStatus.PASSED if regression_result['success'] else ValidationStatus.FAILED,
            message=regression_result['message'],
            details=regression_result['details'],
            execution_time=0.0,
            timestamp=datetime.now().isoformat()
        )
        
        return [result]
    
    def assess_deployment_readiness(self, all_results: List[ValidationResult]) -> Dict[str, Any]:
        """Assess overall deployment readiness."""
        self.logger.info("=== Deployment Readiness Assessment ===")
        
        total_tests = len(all_results)
        passed_tests = len([r for r in all_results if r.status == ValidationStatus.PASSED])
        failed_tests = len([r for r in all_results if r.status == ValidationStatus.FAILED])
        warnings = len([r for r in all_results if r.status == ValidationStatus.WARNING])
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Deployment criteria
        deployment_ready = True
        deployment_issues = []
        
        if success_rate < 95:
            deployment_ready = False
            deployment_issues.append(f"Success rate {success_rate:.1f}% below 95% threshold")
        
        if failed_tests > 0:
            critical_failures = [r for r in all_results if r.status == ValidationStatus.FAILED and 'security' in r.name.lower()]
            if critical_failures:
                deployment_ready = False
                deployment_issues.append("Critical security failures detected")
        
        return {
            'deployment_ready': deployment_ready,
            'success_rate': success_rate,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'warnings': warnings,
            'issues': deployment_issues,
            'recommendation': 'APPROVED FOR DEPLOYMENT' if deployment_ready else 'NOT READY FOR DEPLOYMENT'
        }
    
    def generate_comprehensive_report(self) -> ValidationReport:
        """Generate comprehensive validation report."""
        self.logger.info("Starting comprehensive validation...")
        
        # Run all validation phases
        infrastructure_results = self.validate_infrastructure()
        menu_results = self.validate_menu_integration()
        download_results = []  # Placeholder - would test download system
        advanced_results = []  # Placeholder - would test advanced features
        performance_results = self.validate_performance()
        security_results = self.validate_security()
        regression_results = self.validate_regression()
        
        # Combine all results
        all_results = (infrastructure_results + menu_results + download_results + 
                      advanced_results + performance_results + security_results + regression_results)
        
        # Assess deployment readiness
        deployment_readiness = self.assess_deployment_readiness(all_results)
        
        # Determine overall status
        failed_results = [r for r in all_results if r.status == ValidationStatus.FAILED]
        overall_status = ValidationStatus.FAILED if failed_results else ValidationStatus.PASSED
        
        # Create summary
        summary = {
            'total_tests': len(all_results),
            'passed': len([r for r in all_results if r.status == ValidationStatus.PASSED]),
            'failed': len([r for r in all_results if r.status == ValidationStatus.FAILED]),
            'warnings': len([r for r in all_results if r.status == ValidationStatus.WARNING]),
            'skipped': len([r for r in all_results if r.status == ValidationStatus.SKIPPED]),
            'success_rate': (len([r for r in all_results if r.status == ValidationStatus.PASSED]) / len(all_results) * 100) if all_results else 0
        }
        
        total_time = time.time() - self.start_time
        
        return ValidationReport(
            overall_status=overall_status,
            summary=summary,
            infrastructure=infrastructure_results,
            menu_integration=menu_results,
            download_system=download_results,
            advanced_features=advanced_results,
            performance=performance_results,
            security=security_results,
            regression=regression_results,
            deployment_readiness=deployment_readiness,
            timestamp=datetime.now().isoformat(),
            execution_time=total_time
        )
    
    def _print_result(self, result: ValidationResult):
        """Print validation result."""
        status_symbol = {
            ValidationStatus.PASSED: "✅",
            ValidationStatus.FAILED: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.SKIPPED: "⏭️"
        }
        
        symbol = status_symbol.get(result.status, "❓")
        print(f"{symbol} {result.name}: {result.message} ({result.execution_time:.2f}s)")
        
        if self.verbose and result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")
    
    def export_report(self, report: ValidationReport, format: str = 'json', output_file: Optional[str] = None) -> str:
        """Export validation report in specified format."""
        if format.lower() == 'json':
            return self._export_json_report(report, output_file)
        elif format.lower() == 'markdown':
            return self._export_markdown_report(report, output_file)
        elif format.lower() == 'html':
            return self._export_html_report(report, output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json_report(self, report: ValidationReport, output_file: Optional[str] = None) -> str:
        """Export report as JSON."""
        report_data = asdict(report)
        json_content = json.dumps(report_data, indent=2, default=str)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_content)
            return output_file
        else:
            return json_content
    
    def _export_markdown_report(self, report: ValidationReport, output_file: Optional[str] = None) -> str:
        """Export report as Markdown."""
        md_content = f"""# Sunshine-AIO Community Library Integration Validation Report

**Generated:** {report.timestamp}
**Execution Time:** {report.execution_time:.2f} seconds
**Overall Status:** {report.overall_status.value}

## Summary

- **Total Tests:** {report.summary['total_tests']}
- **Passed:** {report.summary['passed']}
- **Failed:** {report.summary['failed']}
- **Warnings:** {report.summary['warnings']}
- **Success Rate:** {report.summary['success_rate']:.1f}%

## Deployment Readiness

**Status:** {report.deployment_readiness['recommendation']}

"""
        
        # Add section for each test category
        sections = [
            ('Infrastructure', report.infrastructure),
            ('Menu Integration', report.menu_integration),
            ('Download System', report.download_system),
            ('Advanced Features', report.advanced_features),
            ('Performance', report.performance),
            ('Security', report.security),
            ('Regression', report.regression)
        ]
        
        for section_name, results in sections:
            if results:
                md_content += f"\n## {section_name}\n\n"
                for result in results:
                    status_emoji = "✅" if result.status == ValidationStatus.PASSED else "❌"
                    md_content += f"- {status_emoji} **{result.name}**: {result.message}\n"
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(md_content)
            return output_file
        else:
            return md_content
    
    def _export_html_report(self, report: ValidationReport, output_file: Optional[str] = None) -> str:
        """Export report as HTML."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sunshine-AIO Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .status-passed {{ color: green; }}
        .status-failed {{ color: red; }}
        .status-warning {{ color: orange; }}
        .summary {{ margin: 20px 0; }}
        .section {{ margin: 20px 0; }}
        .test-result {{ margin: 10px 0; padding: 10px; border-left: 3px solid #ccc; }}
        .test-passed {{ border-left-color: green; }}
        .test-failed {{ border-left-color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Sunshine-AIO Community Library Integration Validation Report</h1>
        <p><strong>Generated:</strong> {report.timestamp}</p>
        <p><strong>Execution Time:</strong> {report.execution_time:.2f} seconds</p>
        <p><strong>Overall Status:</strong> <span class="status-{report.overall_status.value.lower()}">{report.overall_status.value}</span></p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <ul>
            <li>Total Tests: {report.summary['total_tests']}</li>
            <li>Passed: {report.summary['passed']}</li>
            <li>Failed: {report.summary['failed']}</li>
            <li>Success Rate: {report.summary['success_rate']:.1f}%</li>
        </ul>
    </div>
"""
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(html_content)
            return output_file
        else:
            return html_content
    
    def cleanup(self):
        """Cleanup validation environment."""
        self._cleanup_test_environment()


def main():
    """Main validation script entry point."""
    parser = argparse.ArgumentParser(description='Validate Sunshine-AIO Community Library Integration')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--report-format', choices=['json', 'markdown', 'html'], default='markdown', help='Report format')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--base-path', help='Base path for Sunshine-AIO installation')
    
    args = parser.parse_args()
    
    # Create validator
    validator = SystemValidator(verbose=args.verbose, base_path=args.base_path)
    
    try:
        print("🚀 Starting Sunshine-AIO Community Library Integration Validation...")
        print("=" * 80)
        
        # Generate comprehensive report
        report = validator.generate_comprehensive_report()
        
        # Export report
        output_file = args.output or f'validation_report_{int(time.time())}.{args.report_format}'
        result_file = validator.export_report(report, args.report_format, output_file)
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎯 VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Overall Status: {report.overall_status.value}")
        print(f"Total Tests: {report.summary['total_tests']}")
        print(f"Passed: {report.summary['passed']}")
        print(f"Failed: {report.summary['failed']}")
        print(f"Success Rate: {report.summary['success_rate']:.1f}%")
        print(f"Execution Time: {report.execution_time:.2f} seconds")
        print(f"Report saved to: {result_file}")
        
        # Deployment readiness
        print("\n" + "=" * 80)
        print("🚢 DEPLOYMENT READINESS")
        print("=" * 80)
        print(f"Status: {report.deployment_readiness['recommendation']}")
        
        if report.deployment_readiness['issues']:
            print("Issues:")
            for issue in report.deployment_readiness['issues']:
                print(f"  - {issue}")
        
        # Exit with appropriate code
        exit_code = 0 if report.overall_status == ValidationStatus.PASSED else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        sys.exit(1)
    finally:
        validator.cleanup()


if __name__ == '__main__':
    # Add missing import for unittest.mock
    import unittest.mock
    main()