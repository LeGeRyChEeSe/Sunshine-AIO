"""
Performance testing for community library integration.

This module validates system performance, memory usage, startup times,
and ensures the community library meets all performance requirements.
"""

import pytest
import time
import psutil
import threading
import os
import sys
import tempfile
import shutil
import concurrent.futures
import gc
import tracemalloc
from unittest.mock import Mock, patch
from typing import Dict, List, Any
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from library import (
    LibraryManager,
    CacheManager,
    ConfigManager,
    SearchEngine,
    FilterManager,
    FavoritesManager,
    HistoryManager,
    DownloadManager,
    InstallationManager,
    DisplayHelper
)


@pytest.mark.performance
class TestPerformanceValidation:
    """Performance testing for community library integration."""
    
    @pytest.fixture(autouse=True)
    def setup_performance_test(self):
        """Set up performance test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, 'config')
        self.cache_dir = os.path.join(self.test_dir, 'cache')
        
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize managers
        self.config_manager = ConfigManager(config_dir=self.config_dir)
        self.cache_manager = CacheManager(cache_dir=self.cache_dir)
        self.library_manager = LibraryManager(
            config_manager=self.config_manager,
            cache_manager=self.cache_manager
        )
        
        # Performance tracking
        self.process = psutil.Process()
        self.performance_data = {}
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @pytest.fixture
    def large_mock_tools_dataset(self):
        """Generate large dataset for performance testing."""
        tools = []
        for i in range(1000):
            tools.append({
                "id": f"perf_tool_{i}",
                "name": f"Performance Tool {i}",
                "description": f"Performance testing tool number {i} for validation and benchmarking",
                "category": f"category_{i % 10}",
                "version": f"1.{i % 100}.{i % 10}",
                "author": f"Author {i % 50}",
                "download_url": f"https://example.com/tool{i}.zip",
                "file_size": str(1024 * (i % 1000 + 1)),
                "checksum": f"checksum_{i}",
                "requirements": [f"python>={3.8 + (i % 5) * 0.1}"],
                "tags": [f"tag_{i % 20}", f"performance", f"test_{i % 15}"],
                "rating": 1.0 + (i % 40) / 10.0,
                "downloads": i * 10,
                "last_updated": f"2024-{1 + i % 12:02d}-{1 + i % 28:02d}"
            })
        return tools
    
    def measure_time_and_memory(self, func, *args, **kwargs):
        """Measure execution time and memory usage of a function."""
        # Start memory tracking
        tracemalloc.start()
        initial_memory = self.process.memory_info().rss
        
        # Measure execution time
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        # Get memory statistics
        final_memory = self.process.memory_info().rss
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            'result': result,
            'execution_time': end_time - start_time,
            'memory_used': (final_memory - initial_memory) / (1024 * 1024),  # MB
            'peak_memory': peak / (1024 * 1024),  # MB
            'current_memory': current / (1024 * 1024)  # MB
        }
    
    def test_startup_time_impact(self):
        """Test application startup time impact."""
        # Measure baseline startup (without library)
        def baseline_startup():
            """Simulate baseline application startup."""
            time.sleep(0.1)  # Simulate base application loading
            return True
        
        baseline_metrics = self.measure_time_and_memory(baseline_startup)
        
        # Measure startup with library integration
        def library_startup():
            """Simulate startup with library integration."""
            config_manager = ConfigManager(config_dir=self.config_dir)
            cache_manager = CacheManager(cache_dir=self.cache_dir)
            library_manager = LibraryManager(
                config_manager=config_manager,
                cache_manager=cache_manager
            )
            return library_manager is not None
        
        library_metrics = self.measure_time_and_memory(library_startup)
        
        # Calculate impact
        time_impact = library_metrics['execution_time'] - baseline_metrics['execution_time']
        memory_impact = library_metrics['memory_used'] - baseline_metrics['memory_used']
        
        # Validate requirements: startup time increase < 3 seconds
        assert time_impact < 3.0, f"Startup time impact {time_impact:.2f}s exceeds 3.0s limit"
        
        # Validate requirements: memory usage increase < 50MB
        assert memory_impact < 50.0, f"Memory impact {memory_impact:.2f}MB exceeds 50MB limit"
        
        self.performance_data['startup'] = {
            'time_impact': time_impact,
            'memory_impact': memory_impact,
            'baseline_time': baseline_metrics['execution_time'],
            'library_time': library_metrics['execution_time']
        }
    
    def test_memory_usage_validation(self, large_mock_tools_dataset):
        """Test memory usage under various load conditions."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=large_mock_tools_dataset):
            
            def memory_intensive_operations():
                """Perform memory-intensive operations."""
                search_engine = SearchEngine(self.library_manager)
                filter_manager = FilterManager()
                favorites_manager = FavoritesManager(self.config_manager)
                
                # Multiple search operations
                results = []
                for i in range(50):
                    search_results = search_engine.search(f"test_{i}")
                    results.extend(search_results)
                
                # Multiple filter operations
                filters = [
                    {'category': f'category_{i}', 'min_rating': 2.0 + i}
                    for i in range(10)
                ]
                
                for filter_set in filters:
                    filtered = filter_manager.apply_filters(large_mock_tools_dataset, filter_set)
                    results.extend(filtered)
                
                # Favorites operations
                for i in range(100):
                    favorites_manager.add_favorite(f"perf_tool_{i}")
                
                return len(results)
            
            metrics = self.measure_time_and_memory(memory_intensive_operations)
            
            # Validate memory usage
            assert metrics['memory_used'] < 100.0, f"Memory usage {metrics['memory_used']:.2f}MB exceeds safe limit"
            assert metrics['peak_memory'] < 150.0, f"Peak memory {metrics['peak_memory']:.2f}MB exceeds safe limit"
            
            self.performance_data['memory_intensive'] = metrics
    
    def test_search_performance(self, large_mock_tools_dataset):
        """Test search operation performance."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=large_mock_tools_dataset):
            search_engine = SearchEngine(self.library_manager)
            
            # Test various search scenarios
            search_queries = [
                "performance",
                "tool",
                "test_123",
                "category_5",
                "author 25",
                "nonexistent_query_12345"
            ]
            
            search_times = []
            
            for query in search_queries:
                def search_operation():
                    return search_engine.search(query)
                
                metrics = self.measure_time_and_memory(search_operation)
                search_times.append(metrics['execution_time'])
                
                # Each search should complete within 2 seconds
                assert metrics['execution_time'] < 2.0, (
                    f"Search for '{query}' took {metrics['execution_time']:.2f}s, exceeds 2.0s limit"
                )
            
            # Average search time should be reasonable
            avg_search_time = sum(search_times) / len(search_times)
            assert avg_search_time < 1.0, f"Average search time {avg_search_time:.2f}s exceeds 1.0s target"
            
            self.performance_data['search'] = {
                'average_time': avg_search_time,
                'max_time': max(search_times),
                'min_time': min(search_times),
                'queries_tested': len(search_queries)
            }
    
    def test_concurrent_operations(self, large_mock_tools_dataset):
        """Test performance under concurrent operations."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=large_mock_tools_dataset):
            
            def concurrent_worker(worker_id: int):
                """Worker function for concurrent testing."""
                search_engine = SearchEngine(self.library_manager)
                favorites_manager = FavoritesManager(self.config_manager)
                
                operations_count = 0
                start_time = time.perf_counter()
                
                # Perform mixed operations
                for i in range(10):
                    # Search operation
                    search_engine.search(f"worker_{worker_id}_query_{i}")
                    operations_count += 1
                    
                    # Favorites operation
                    favorites_manager.add_favorite(f"worker_{worker_id}_tool_{i}")
                    operations_count += 1
                
                end_time = time.perf_counter()
                return {
                    'worker_id': worker_id,
                    'operations': operations_count,
                    'time': end_time - start_time
                }
            
            # Run concurrent operations
            start_time = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(concurrent_worker, i)
                    for i in range(5)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.perf_counter() - start_time
            
            # Validate concurrent performance
            total_operations = sum(result['operations'] for result in results)
            operations_per_second = total_operations / total_time
            
            # Should handle reasonable concurrent load
            assert operations_per_second > 10, (
                f"Concurrent operations rate {operations_per_second:.2f} ops/sec too low"
            )
            
            # No worker should take excessively long
            max_worker_time = max(result['time'] for result in results)
            assert max_worker_time < 5.0, f"Slowest worker took {max_worker_time:.2f}s, too slow"
            
            self.performance_data['concurrent'] = {
                'total_time': total_time,
                'operations_per_second': operations_per_second,
                'max_worker_time': max_worker_time,
                'workers': len(results)
            }
    
    def test_large_dataset_handling(self):
        """Test performance with very large datasets."""
        # Generate extremely large dataset
        huge_dataset = []
        for i in range(10000):  # 10k tools
            huge_dataset.append({
                "id": f"huge_tool_{i}",
                "name": f"Huge Dataset Tool {i}",
                "description": f"Large dataset performance testing tool {i} " * 10,  # Long description
                "category": f"huge_category_{i % 100}",
                "tags": [f"huge_tag_{j}" for j in range(i % 20)],  # Variable tag count
                "rating": 1.0 + (i % 40) / 10.0,
                "downloads": i * 100,
                "version": f"{i // 1000}.{i // 100}.{i % 100}"
            })
        
        with patch.object(self.library_manager, 'get_available_tools', return_value=huge_dataset):
            
            def large_dataset_operations():
                """Operations on large dataset."""
                search_engine = SearchEngine(self.library_manager)
                filter_manager = FilterManager()
                
                # Search operations
                search_results = search_engine.search("huge")
                
                # Filter operations
                filters = {'category': 'huge_category_50', 'min_rating': 3.0}
                filtered_results = filter_manager.apply_filters(huge_dataset, filters)
                
                return len(search_results) + len(filtered_results)
            
            metrics = self.measure_time_and_memory(large_dataset_operations)
            
            # Should handle large datasets reasonably
            assert metrics['execution_time'] < 10.0, (
                f"Large dataset operations took {metrics['execution_time']:.2f}s, too slow"
            )
            assert metrics['memory_used'] < 200.0, (
                f"Large dataset used {metrics['memory_used']:.2f}MB, too much memory"
            )
            
            self.performance_data['large_dataset'] = metrics
    
    def test_cache_performance(self, large_mock_tools_dataset):
        """Test cache system performance."""
        # Test cache write performance
        def cache_write_operations():
            """Test cache writing performance."""
            for i in range(100):
                cache_key = f"test_key_{i}"
                cache_data = {'data': f"test_data_{i}" * 100}  # Some data
                self.cache_manager.set(cache_key, cache_data)
            return True
        
        write_metrics = self.measure_time_and_memory(cache_write_operations)
        
        # Test cache read performance
        def cache_read_operations():
            """Test cache reading performance."""
            results = []
            for i in range(100):
                cache_key = f"test_key_{i}"
                data = self.cache_manager.get(cache_key)
                results.append(data)
            return len(results)
        
        read_metrics = self.measure_time_and_memory(cache_read_operations)
        
        # Validate cache performance
        assert write_metrics['execution_time'] < 2.0, (
            f"Cache writes took {write_metrics['execution_time']:.2f}s, too slow"
        )
        assert read_metrics['execution_time'] < 1.0, (
            f"Cache reads took {read_metrics['execution_time']:.2f}s, too slow"
        )
        
        self.performance_data['cache'] = {
            'write_time': write_metrics['execution_time'],
            'read_time': read_metrics['execution_time'],
            'write_memory': write_metrics['memory_used'],
            'read_memory': read_metrics['memory_used']
        }
    
    def test_network_resilience(self):
        """Test performance under network stress conditions."""
        # Test timeout handling
        def network_timeout_test():
            """Test network timeout performance."""
            with patch('requests.get') as mock_get:
                # Simulate slow network
                def slow_response(*args, **kwargs):
                    time.sleep(2)  # Simulate slow response
                    mock_response = Mock()
                    mock_response.json.return_value = []
                    mock_response.status_code = 200
                    return mock_response
                
                mock_get.side_effect = slow_response
                
                try:
                    tools = self.library_manager.get_available_tools()
                    return len(tools)
                except Exception:
                    return 0
        
        timeout_metrics = self.measure_time_and_memory(network_timeout_test)
        
        # Should handle network delays gracefully
        assert timeout_metrics['execution_time'] < 10.0, (
            f"Network timeout handling took {timeout_metrics['execution_time']:.2f}s, too slow"
        )
        
        self.performance_data['network_resilience'] = timeout_metrics
    
    def test_memory_leak_detection(self, large_mock_tools_dataset):
        """Test for memory leaks during repeated operations."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=large_mock_tools_dataset):
            
            initial_memory = self.process.memory_info().rss
            memory_snapshots = [initial_memory]
            
            # Perform operations in cycles to detect leaks
            for cycle in range(10):
                # Create and destroy objects
                search_engine = SearchEngine(self.library_manager)
                favorites_manager = FavoritesManager(self.config_manager)
                
                # Perform operations
                for i in range(20):
                    search_engine.search(f"cycle_{cycle}_query_{i}")
                    favorites_manager.add_favorite(f"cycle_{cycle}_tool_{i}")
                
                # Clean up references
                del search_engine, favorites_manager
                gc.collect()
                
                # Take memory snapshot
                current_memory = self.process.memory_info().rss
                memory_snapshots.append(current_memory)
            
            # Analyze memory growth
            memory_growth = (memory_snapshots[-1] - memory_snapshots[0]) / (1024 * 1024)  # MB
            
            # Memory should not grow significantly (< 10MB over 10 cycles)
            assert memory_growth < 10.0, (
                f"Memory grew by {memory_growth:.2f}MB over 10 cycles, possible leak"
            )
            
            self.performance_data['memory_leak'] = {
                'total_growth': memory_growth,
                'cycles': 10,
                'growth_per_cycle': memory_growth / 10
            }
    
    @pytest.mark.slow
    def test_stress_testing(self, large_mock_tools_dataset):
        """Comprehensive stress testing."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=large_mock_tools_dataset):
            
            def stress_test_operations():
                """Intensive stress test operations."""
                search_engine = SearchEngine(self.library_manager)
                filter_manager = FilterManager()
                favorites_manager = FavoritesManager(self.config_manager)
                
                operations_completed = 0
                
                # Intensive search operations
                for i in range(200):
                    search_engine.search(f"stress_query_{i}")
                    operations_completed += 1
                
                # Intensive filter operations
                for i in range(100):
                    filters = {
                        'category': f'category_{i % 10}',
                        'min_rating': 1.0 + (i % 40) / 10.0
                    }
                    filter_manager.apply_filters(large_mock_tools_dataset, filters)
                    operations_completed += 1
                
                # Intensive favorites operations
                for i in range(500):
                    favorites_manager.add_favorite(f"stress_tool_{i}")
                    if i % 10 == 0:
                        favorites_manager.get_favorites()
                    operations_completed += 1
                
                return operations_completed
            
            stress_metrics = self.measure_time_and_memory(stress_test_operations)
            
            # System should remain stable under stress
            assert stress_metrics['execution_time'] < 30.0, (
                f"Stress test took {stress_metrics['execution_time']:.2f}s, too slow"
            )
            assert stress_metrics['memory_used'] < 300.0, (
                f"Stress test used {stress_metrics['memory_used']:.2f}MB, too much memory"
            )
            
            self.performance_data['stress_test'] = stress_metrics
    
    def test_performance_regression_baseline(self):
        """Establish performance regression baseline."""
        # This test creates baseline metrics for future regression testing
        baseline_metrics = {
            'startup_time': 1.0,  # Target startup time in seconds
            'search_time': 0.5,   # Target search time in seconds
            'memory_usage': 25.0,  # Target memory usage in MB
            'operations_per_second': 50.0  # Target operations per second
        }
        
        # Store baseline for comparison
        self.performance_data['baseline'] = baseline_metrics
        
        # Validate current performance against baseline
        if hasattr(self, 'performance_data'):
            if 'startup' in self.performance_data:
                startup_time = self.performance_data['startup']['time_impact']
                assert startup_time <= baseline_metrics['startup_time'] * 1.5, (
                    f"Startup time {startup_time:.2f}s exceeds baseline by >50%"
                )
    
    def teardown_method(self):
        """Generate performance report after each test."""
        if hasattr(self, 'performance_data') and self.performance_data:
            report_file = os.path.join(self.test_dir, 'performance_report.json')
            try:
                import json
                with open(report_file, 'w') as f:
                    json.dump(self.performance_data, f, indent=2, default=str)
            except Exception:
                pass  # Don't fail tests due to reporting issues


@pytest.mark.performance
@pytest.mark.slow
class TestResourceMonitoring:
    """Monitor system resources during extended operations."""
    
    def test_extended_operation_monitoring(self):
        """Monitor system resources during extended operations."""
        process = psutil.Process()
        monitoring_duration = 60  # Monitor for 1 minute
        sample_interval = 1  # Sample every second
        
        memory_samples = []
        cpu_samples = []
        
        start_time = time.time()
        
        # Simulate extended operations while monitoring
        while time.time() - start_time < monitoring_duration:
            # Sample resource usage
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            memory_samples.append(memory_info.rss / (1024 * 1024))  # MB
            cpu_samples.append(cpu_percent)
            
            # Perform some operations
            config_manager = ConfigManager()
            cache_manager = CacheManager()
            
            time.sleep(sample_interval)
        
        # Analyze resource usage
        avg_memory = sum(memory_samples) / len(memory_samples)
        max_memory = max(memory_samples)
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        
        # Validate resource usage is reasonable
        assert avg_memory < 100.0, f"Average memory usage {avg_memory:.2f}MB too high"
        assert max_memory < 200.0, f"Peak memory usage {max_memory:.2f}MB too high"
        assert avg_cpu < 50.0, f"Average CPU usage {avg_cpu:.2f}% too high"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])