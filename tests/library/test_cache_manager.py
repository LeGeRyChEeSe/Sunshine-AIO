"""
Comprehensive unit tests for CacheManager and CacheEntry.

Tests cover cache initialization, data storage/retrieval, TTL and LRU eviction,
file caching with integrity checks, thread safety, and cleanup operations.
"""

import pytest
import os
import json
import time
import threading
import tempfile
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta

from library.cache_manager import CacheManager, CacheEntry


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def test_cache_entry_initialization_basic(self):
        """Test basic CacheEntry initialization."""
        entry = CacheEntry("test_key", {"data": "value"})
        
        assert entry.key == "test_key"
        assert entry.data == {"data": "value"}
        assert entry.ttl == 3600  # Default TTL
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.expires_at, datetime)
        assert entry.access_count == 0
        assert entry.last_accessed == entry.created_at
    
    def test_cache_entry_initialization_custom_ttl(self):
        """Test CacheEntry initialization with custom TTL."""
        entry = CacheEntry("test_key", "test_data", ttl=1800)
        
        assert entry.ttl == 1800
        expected_expiry = entry.created_at + timedelta(seconds=1800)
        assert abs((entry.expires_at - expected_expiry).total_seconds()) < 1
    
    def test_cache_entry_initialization_custom_created_at(self):
        """Test CacheEntry initialization with custom creation time."""
        custom_time = datetime(2024, 1, 15, 10, 30, 0)
        entry = CacheEntry("test_key", "test_data", created_at=custom_time)
        
        assert entry.created_at == custom_time
        assert entry.last_accessed == custom_time
        expected_expiry = custom_time + timedelta(seconds=3600)
        assert entry.expires_at == expected_expiry
    
    def test_cache_entry_is_expired_fresh(self):
        """Test is_expired for fresh entry."""
        entry = CacheEntry("test_key", "test_data", ttl=3600)
        
        assert entry.is_expired() is False
    
    def test_cache_entry_is_expired_old(self):
        """Test is_expired for expired entry."""
        old_time = datetime.now() - timedelta(seconds=7200)  # 2 hours ago
        entry = CacheEntry("test_key", "test_data", ttl=3600, created_at=old_time)
        
        assert entry.is_expired() is True
    
    def test_cache_entry_refresh_default(self):
        """Test refresh with default TTL."""
        old_time = datetime.now() - timedelta(seconds=1800)
        entry = CacheEntry("test_key", "test_data", ttl=3600, created_at=old_time)
        
        entry.refresh()
        
        # Should extend expiry time
        assert entry.expires_at > datetime.now() + timedelta(seconds=3500)
        assert entry.ttl == 3600  # Should keep original TTL
    
    def test_cache_entry_refresh_custom_ttl(self):
        """Test refresh with custom TTL."""
        entry = CacheEntry("test_key", "test_data", ttl=3600)
        
        entry.refresh(1800)
        
        assert entry.ttl == 1800
        expected_expiry = datetime.now() + timedelta(seconds=1800)
        assert abs((entry.expires_at - expected_expiry).total_seconds()) < 5
    
    def test_cache_entry_access(self):
        """Test access method updates statistics."""
        entry = CacheEntry("test_key", {"important": "data"})
        initial_access_time = entry.last_accessed
        
        # Small delay to ensure time difference
        time.sleep(0.01)
        
        data = entry.access()
        
        assert data == {"important": "data"}
        assert entry.access_count == 1
        assert entry.last_accessed > initial_access_time
    
    def test_cache_entry_access_multiple(self):
        """Test multiple accesses update count correctly."""
        entry = CacheEntry("test_key", "data")
        
        for i in range(5):
            entry.access()
        
        assert entry.access_count == 5
    
    def test_cache_entry_to_dict(self):
        """Test CacheEntry serialization to dict."""
        entry = CacheEntry(
            "test_key", 
            {"nested": {"data": "value"}}, 
            ttl=1800
        )
        entry.access()  # Update access stats
        
        entry_dict = entry.to_dict()
        
        assert entry_dict['key'] == "test_key"
        assert entry_dict['data'] == {"nested": {"data": "value"}}
        assert entry_dict['ttl'] == 1800
        assert entry_dict['access_count'] == 1
        assert 'created_at' in entry_dict
        assert 'expires_at' in entry_dict
        assert 'last_accessed' in entry_dict
        
        # Check ISO format dates
        datetime.fromisoformat(entry_dict['created_at'])
        datetime.fromisoformat(entry_dict['expires_at'])
        datetime.fromisoformat(entry_dict['last_accessed'])
    
    def test_cache_entry_from_dict(self):
        """Test CacheEntry deserialization from dict."""
        data = {
            'key': 'restored_key',
            'data': ['list', 'data'],
            'ttl': 7200,
            'created_at': '2024-01-15T10:30:00',
            'expires_at': '2024-01-15T12:30:00',
            'access_count': 3,
            'last_accessed': '2024-01-15T11:00:00'
        }
        
        entry = CacheEntry.from_dict(data)
        
        assert entry.key == 'restored_key'
        assert entry.data == ['list', 'data']
        assert entry.ttl == 7200
        assert entry.access_count == 3
        assert entry.created_at == datetime.fromisoformat('2024-01-15T10:30:00')
        assert entry.expires_at == datetime.fromisoformat('2024-01-15T12:30:00')
        assert entry.last_accessed == datetime.fromisoformat('2024-01-15T11:00:00')
    
    def test_cache_entry_from_dict_minimal(self):
        """Test CacheEntry from_dict with minimal data."""
        data = {
            'key': 'minimal_key',
            'data': 'minimal_data',
            'ttl': 3600,
            'created_at': '2024-01-15T10:30:00',
            'expires_at': '2024-01-15T11:30:00'
        }
        
        entry = CacheEntry.from_dict(data)
        
        assert entry.key == 'minimal_key'
        assert entry.data == 'minimal_data'
        assert entry.access_count == 0  # Default
        assert entry.last_accessed == entry.created_at  # Fallback


class TestCacheManagerInitialization:
    """Test CacheManager initialization and configuration."""
    
    def test_cache_manager_initialization_basic(self, cache_manager):
        """Test basic CacheManager initialization."""
        assert cache_manager.cache_dir is not None
        assert cache_manager.max_size == 1000  # Default
        assert cache_manager.default_ttl == 3600  # Default
        assert cache_manager.cleanup_interval == 300  # Default
        assert cache_manager._entries == {}
        assert cache_manager._stats['hits'] == 0
        assert cache_manager._stats['misses'] == 0
    
    def test_cache_manager_initialization_custom(self, temp_dir):
        """Test CacheManager initialization with custom parameters."""
        custom_cache_dir = os.path.join(temp_dir, "custom_cache")
        
        manager = CacheManager(
            cache_dir=custom_cache_dir,
            max_size=500,
            default_ttl=1800,
            cleanup_interval=600
        )
        
        assert manager.cache_dir == custom_cache_dir
        assert manager.max_size == 500
        assert manager.default_ttl == 1800
        assert manager.cleanup_interval == 600
    
    @patch('os.makedirs')
    def test_cache_manager_ensure_cache_directory(self, mock_makedirs, temp_dir):
        """Test cache directory creation."""
        cache_dir = os.path.join(temp_dir, "new_cache")
        
        CacheManager(cache_dir=cache_dir)
        
        mock_makedirs.assert_called_once_with(cache_dir, exist_ok=True)
    
    @patch('os.makedirs', side_effect=OSError("Permission denied"))
    def test_cache_manager_directory_creation_failure(self, mock_makedirs, temp_dir):
        """Test handling of cache directory creation failure."""
        cache_dir = os.path.join(temp_dir, "failed_cache")
        
        with pytest.raises(OSError):
            CacheManager(cache_dir=cache_dir)
    
    def test_cache_manager_initialize_method(self, cache_manager):
        """Test CacheManager initialize method."""
        with patch.object(cache_manager, '_start_cleanup_thread') as mock_start, \
             patch.object(cache_manager, '_load_persistent_cache') as mock_load:
            
            result = cache_manager.initialize()
            
            assert result is True
            assert cache_manager._initialized is True
            mock_start.assert_called_once()
            mock_load.assert_called_once()
    
    def test_cache_manager_initialize_exception(self, cache_manager):
        """Test CacheManager initialize with exception."""
        with patch.object(cache_manager, '_start_cleanup_thread', side_effect=Exception("Thread error")):
            
            result = cache_manager.initialize()
            
            assert result is False
            assert cache_manager._initialized is False


class TestCacheManagerBasicOperations:
    """Test basic cache operations."""
    
    def test_cache_put_and_get_basic(self, cache_manager):
        """Test basic put and get operations."""
        cache_manager.initialize()
        
        cache_manager.put("test_key", {"data": "value"})
        result = cache_manager.get("test_key")
        
        assert result == {"data": "value"}
        assert cache_manager._stats['hits'] == 1
        assert cache_manager._stats['misses'] == 0
    
    def test_cache_put_with_custom_ttl(self, cache_manager):
        """Test put with custom TTL."""
        cache_manager.initialize()
        
        cache_manager.put("ttl_key", "ttl_data", ttl=1800)
        
        entry = cache_manager._entries["ttl_key"]
        assert entry.ttl == 1800
        assert entry.data == "ttl_data"
    
    def test_cache_get_nonexistent(self, cache_manager):
        """Test get for non-existent key."""
        cache_manager.initialize()
        
        result = cache_manager.get("nonexistent_key")
        
        assert result is None
        assert cache_manager._stats['misses'] == 1
        assert cache_manager._stats['hits'] == 0
    
    def test_cache_get_with_default(self, cache_manager):
        """Test get with default value."""
        cache_manager.initialize()
        
        result = cache_manager.get("nonexistent_key", default="default_value")
        
        assert result == "default_value"
    
    def test_cache_get_expired_entry(self, cache_manager):
        """Test get for expired entry."""
        cache_manager.initialize()
        
        # Create expired entry
        old_time = datetime.now() - timedelta(seconds=7200)
        expired_entry = CacheEntry("expired_key", "expired_data", ttl=3600, created_at=old_time)
        cache_manager._entries["expired_key"] = expired_entry
        
        result = cache_manager.get("expired_key")
        
        assert result is None
        assert "expired_key" not in cache_manager._entries  # Should be removed
        assert cache_manager._stats['misses'] == 1
    
    def test_cache_exists_key(self, cache_manager):
        """Test exists method."""
        cache_manager.initialize()
        
        cache_manager.put("existing_key", "data")
        
        assert cache_manager.exists("existing_key") is True
        assert cache_manager.exists("nonexistent_key") is False
    
    def test_cache_exists_expired_key(self, cache_manager):
        """Test exists with expired key."""
        cache_manager.initialize()
        
        # Create expired entry
        old_time = datetime.now() - timedelta(seconds=7200)
        expired_entry = CacheEntry("expired_key", "data", ttl=3600, created_at=old_time)
        cache_manager._entries["expired_key"] = expired_entry
        
        assert cache_manager.exists("expired_key") is False
        assert "expired_key" not in cache_manager._entries
    
    def test_cache_delete_key(self, cache_manager):
        """Test delete operation."""
        cache_manager.initialize()
        
        cache_manager.put("delete_me", "data")
        assert cache_manager.exists("delete_me") is True
        
        result = cache_manager.delete("delete_me")
        
        assert result is True
        assert cache_manager.exists("delete_me") is False
    
    def test_cache_delete_nonexistent(self, cache_manager):
        """Test delete non-existent key."""
        cache_manager.initialize()
        
        result = cache_manager.delete("nonexistent_key")
        
        assert result is False
    
    def test_cache_clear_all(self, cache_manager):
        """Test clear all entries."""
        cache_manager.initialize()
        
        # Add multiple entries
        for i in range(5):
            cache_manager.put(f"key_{i}", f"data_{i}")
        
        assert len(cache_manager._entries) == 5
        
        cache_manager.clear()
        
        assert len(cache_manager._entries) == 0
        assert cache_manager._stats['hits'] == 0
        assert cache_manager._stats['misses'] == 0


class TestCacheManagerEvictionPolicies:
    """Test cache eviction policies."""
    
    def test_cache_size_limit_eviction(self, temp_dir):
        """Test LRU eviction when size limit is reached."""
        manager = CacheManager(cache_dir=temp_dir, max_size=3)
        manager.initialize()
        
        # Fill cache to limit
        for i in range(3):
            manager.put(f"key_{i}", f"data_{i}")
        
        assert len(manager._entries) == 3
        
        # Access key_1 to make it recently used
        manager.get("key_1")
        
        # Add one more to trigger eviction
        manager.put("key_3", "data_3")
        
        # key_0 should be evicted (least recently used)
        assert len(manager._entries) == 3
        assert "key_0" not in manager._entries
        assert "key_1" in manager._entries  # Recently accessed
        assert "key_2" in manager._entries
        assert "key_3" in manager._entries
    
    def test_cache_ttl_expiration_cleanup(self, cache_manager):
        """Test TTL-based cleanup of expired entries."""
        cache_manager.initialize()
        
        # Create entries with different expiration times
        old_time = datetime.now() - timedelta(seconds=7200)
        recent_time = datetime.now() - timedelta(seconds=1800)
        
        # Expired entry
        expired_entry = CacheEntry("expired", "data", ttl=3600, created_at=old_time)
        # Valid entry
        valid_entry = CacheEntry("valid", "data", ttl=7200, created_at=recent_time)
        
        cache_manager._entries["expired"] = expired_entry
        cache_manager._entries["valid"] = valid_entry
        
        # Run cleanup
        removed_count = cache_manager._cleanup_expired()
        
        assert removed_count == 1
        assert "expired" not in cache_manager._entries
        assert "valid" in cache_manager._entries
    
    def test_cache_cleanup_empty_cache(self, cache_manager):
        """Test cleanup on empty cache."""
        cache_manager.initialize()
        
        removed_count = cache_manager._cleanup_expired()
        
        assert removed_count == 0
    
    def test_cache_cleanup_no_expired(self, cache_manager):
        """Test cleanup with no expired entries."""
        cache_manager.initialize()
        
        # Add fresh entries
        for i in range(3):
            cache_manager.put(f"key_{i}", f"data_{i}")
        
        removed_count = cache_manager._cleanup_expired()
        
        assert removed_count == 0
        assert len(cache_manager._entries) == 3


class TestCacheManagerFileOperations:
    """Test cache file operations and persistence."""
    
    def test_cache_file_put_and_get(self, cache_manager, temp_dir):
        """Test file caching operations."""
        cache_manager.initialize()
        
        # Create a test file
        test_file = os.path.join(temp_dir, "test_file.txt")
        test_content = b"This is test file content"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Cache the file
        cache_manager.put_file("test_file", test_file)
        
        # Retrieve the file
        retrieved_path = cache_manager.get_file("test_file")
        
        assert retrieved_path is not None
        assert os.path.exists(retrieved_path)
        
        # Verify content
        with open(retrieved_path, 'rb') as f:
            retrieved_content = f.read()
        
        assert retrieved_content == test_content
    
    def test_cache_file_put_nonexistent_source(self, cache_manager):
        """Test caching non-existent source file."""
        cache_manager.initialize()
        
        result = cache_manager.put_file("missing", "/nonexistent/file.txt")
        
        assert result is False
    
    def test_cache_file_get_nonexistent(self, cache_manager):
        """Test retrieving non-existent cached file."""
        cache_manager.initialize()
        
        result = cache_manager.get_file("nonexistent_file")
        
        assert result is None
    
    def test_cache_file_with_checksum_verification(self, cache_manager, temp_dir):
        """Test file caching with checksum verification."""
        cache_manager.initialize()
        
        # Create test file
        test_file = os.path.join(temp_dir, "checksum_test.txt")
        test_content = b"Content for checksum test"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Cache with checksum
        result = cache_manager.put_file("checksum_file", test_file, checksum="auto")
        
        assert result is True
        
        # Retrieve and verify
        retrieved_path = cache_manager.get_file("checksum_file", verify_checksum=True)
        
        assert retrieved_path is not None
    
    @patch('shutil.copy2', side_effect=OSError("Copy failed"))
    def test_cache_file_put_copy_failure(self, mock_copy, cache_manager, temp_dir):
        """Test handling of file copy failure."""
        cache_manager.initialize()
        
        test_file = os.path.join(temp_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        result = cache_manager.put_file("copy_fail", test_file)
        
        assert result is False
    
    def test_cache_file_corrupted_cached_file(self, cache_manager, temp_dir):
        """Test handling of corrupted cached file."""
        cache_manager.initialize()
        
        # Create and cache a file
        test_file = os.path.join(temp_dir, "original.txt")
        test_content = b"Original content"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        cache_manager.put_file("corrupt_test", test_file, checksum="auto")
        
        # Corrupt the cached file
        cached_files = cache_manager._entries["corrupt_test"].data
        cached_path = cached_files['file_path']
        with open(cached_path, 'w') as f:
            f.write("corrupted content")
        
        # Try to retrieve with checksum verification
        retrieved_path = cache_manager.get_file("corrupt_test", verify_checksum=True)
        
        # Should return None due to checksum mismatch
        assert retrieved_path is None


class TestCacheManagerStatistics:
    """Test cache statistics and monitoring."""
    
    def test_cache_statistics_tracking(self, cache_manager):
        """Test statistics tracking for cache operations."""
        cache_manager.initialize()
        
        # Perform various operations
        cache_manager.put("key1", "data1")
        cache_manager.put("key2", "data2")
        
        cache_manager.get("key1")  # Hit
        cache_manager.get("key1")  # Hit
        cache_manager.get("nonexistent")  # Miss
        
        stats = cache_manager.get_stats()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['total_entries'] == 2
        assert stats['hit_rate'] == 2/3  # 2 hits out of 3 accesses
    
    def test_cache_statistics_reset(self, cache_manager):
        """Test statistics reset functionality."""
        cache_manager.initialize()
        
        # Generate some stats
        cache_manager.put("key", "data")
        cache_manager.get("key")
        cache_manager.get("nonexistent")
        
        assert cache_manager._stats['hits'] == 1
        assert cache_manager._stats['misses'] == 1
        
        # Reset stats
        cache_manager._reset_stats()
        
        stats = cache_manager.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0.0
    
    def test_cache_statistics_with_empty_cache(self, cache_manager):
        """Test statistics with empty cache."""
        cache_manager.initialize()
        
        stats = cache_manager.get_stats()
        
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['total_entries'] == 0
        assert stats['hit_rate'] == 0.0
    
    def test_cache_get_info(self, cache_manager):
        """Test get_info method returns comprehensive information."""
        cache_manager.initialize()
        
        # Add some data
        cache_manager.put("info_key", "info_data")
        
        info = cache_manager.get_info()
        
        assert 'cache_dir' in info
        assert 'max_size' in info
        assert 'default_ttl' in info
        assert 'cleanup_interval' in info
        assert 'initialized' in info
        assert 'stats' in info
        
        assert info['initialized'] is True
        assert info['stats']['total_entries'] == 1


class TestCacheManagerThreadSafety:
    """Test cache thread safety."""
    
    def test_cache_thread_safety_concurrent_access(self, cache_manager):
        """Test thread-safe concurrent access to cache."""
        cache_manager.initialize()
        
        # Pre-populate cache
        for i in range(10):
            cache_manager.put(f"key_{i}", f"data_{i}")
        
        results = []
        errors = []
        
        def worker(thread_id):
            try:
                for i in range(20):
                    key = f"key_{i % 10}"
                    value = cache_manager.get(key)
                    results.append((thread_id, key, value))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for t_id in range(5):
            thread = threading.Thread(target=worker, args=(t_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no errors and consistent results
        assert len(errors) == 0
        assert len(results) == 100  # 5 threads * 20 operations each
        
        # Verify data consistency
        for thread_id, key, value in results:
            expected_value = f"data_{key.split('_')[1]}"
            assert value == expected_value
    
    def test_cache_thread_safety_concurrent_modifications(self, cache_manager):
        """Test thread-safe concurrent modifications."""
        cache_manager.initialize()
        
        errors = []
        
        def modifier_worker(thread_id):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_data_{i}"
                    cache_manager.put(key, value)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        def reader_worker(thread_id):
            try:
                for i in range(50):
                    # Try to read from different thread keys
                    for t_id in range(3):
                        key = f"thread_{t_id}_key_{i % 10}"
                        cache_manager.get(key)  # May return None, that's fine
            except Exception as e:
                errors.append((f"reader_{thread_id}", str(e)))
        
        # Start modifier and reader threads
        threads = []
        
        # 3 modifier threads
        for t_id in range(3):
            thread = threading.Thread(target=modifier_worker, args=(t_id,))
            threads.append(thread)
            thread.start()
        
        # 2 reader threads
        for t_id in range(2):
            thread = threading.Thread(target=reader_worker, args=(t_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        
        # Verify some entries were created
        assert len(cache_manager._entries) >= 10  # At least some entries


class TestCacheManagerPersistence:
    """Test cache persistence functionality."""
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    @patch('os.path.exists', return_value=True)
    def test_save_persistent_cache(self, mock_exists, mock_json_dump, mock_file, cache_manager):
        """Test saving cache to persistent storage."""
        cache_manager.initialize()
        
        # Add some entries
        cache_manager.put("persist_key1", "persist_data1")
        cache_manager.put("persist_key2", {"nested": "data"})
        
        result = cache_manager._save_persistent_cache()
        
        assert result is True
        mock_file.assert_called_once()
        mock_json_dump.assert_called_once()
    
    @patch('builtins.open', side_effect=OSError("Write failed"))
    def test_save_persistent_cache_failure(self, mock_open, cache_manager):
        """Test handling of persistent cache save failure."""
        cache_manager.initialize()
        
        cache_manager.put("test_key", "test_data")
        
        result = cache_manager._save_persistent_cache()
        
        assert result is False
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"entries": {}}')
    @patch('json.load')
    @patch('os.path.exists', return_value=True)
    def test_load_persistent_cache_success(self, mock_exists, mock_json_load, mock_file, cache_manager):
        """Test loading cache from persistent storage."""
        persistent_data = {
            "entries": {
                "loaded_key": {
                    "key": "loaded_key",
                    "data": "loaded_data",
                    "ttl": 3600,
                    "created_at": "2024-01-15T10:30:00",
                    "expires_at": "2024-01-15T11:30:00",
                    "access_count": 0,
                    "last_accessed": "2024-01-15T10:30:00"
                }
            },
            "stats": {"hits": 5, "misses": 2}
        }
        mock_json_load.return_value = persistent_data
        
        result = cache_manager._load_persistent_cache()
        
        assert result is True
        assert "loaded_key" in cache_manager._entries
        assert cache_manager._stats["hits"] == 5
        assert cache_manager._stats["misses"] == 2
    
    @patch('os.path.exists', return_value=False)
    def test_load_persistent_cache_no_file(self, mock_exists, cache_manager):
        """Test loading when no persistent cache file exists."""
        result = cache_manager._load_persistent_cache()
        
        assert result is True  # Should succeed (no file to load)
        assert len(cache_manager._entries) == 0
    
    @patch('builtins.open', side_effect=OSError("Read failed"))
    @patch('os.path.exists', return_value=True)
    def test_load_persistent_cache_failure(self, mock_exists, mock_open, cache_manager):
        """Test handling of persistent cache load failure."""
        result = cache_manager._load_persistent_cache()
        
        assert result is False


@pytest.mark.integration
class TestCacheManagerIntegration:
    """Integration tests for CacheManager."""
    
    def test_full_cache_lifecycle(self, temp_dir):
        """Test complete cache lifecycle with real files."""
        cache_dir = os.path.join(temp_dir, "integration_cache")
        manager = CacheManager(cache_dir=cache_dir, max_size=10)
        
        # Initialize
        result = manager.initialize()
        assert result is True
        
        # Add various types of data
        manager.put("string_data", "test_string")
        manager.put("dict_data", {"key": "value", "nested": {"data": 123}})
        manager.put("list_data", [1, 2, 3, "four", {"five": 6}])
        
        # Create and cache a file
        test_file = os.path.join(temp_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("Test file content for integration test")
        
        file_cached = manager.put_file("test_file", test_file)
        assert file_cached is True
        
        # Verify all data can be retrieved
        assert manager.get("string_data") == "test_string"
        assert manager.get("dict_data")["nested"]["data"] == 123
        assert manager.get("list_data")[3] == "four"
        
        cached_file_path = manager.get_file("test_file")
        assert cached_file_path is not None
        assert os.path.exists(cached_file_path)
        
        # Check statistics
        stats = manager.get_stats()
        assert stats["hits"] >= 4
        assert stats["total_entries"] == 4
        
        # Test cleanup and shutdown
        manager._cleanup_expired()
        
        # Shutdown should not crash
        if hasattr(manager, 'shutdown'):
            manager.shutdown()
    
    def test_cache_persistence_integration(self, temp_dir):
        """Test cache persistence across manager instances."""
        cache_dir = os.path.join(temp_dir, "persistence_cache")
        
        # First manager instance
        manager1 = CacheManager(cache_dir=cache_dir)
        manager1.initialize()
        
        # Add data
        manager1.put("persistent_key", "persistent_value")
        manager1.put("complex_data", {"numbers": [1, 2, 3], "text": "test"})
        
        # Save and shutdown first manager
        manager1._save_persistent_cache()
        
        # Create second manager instance
        manager2 = CacheManager(cache_dir=cache_dir)
        manager2.initialize()
        
        # Should load previously saved data
        assert manager2.get("persistent_key") == "persistent_value"
        assert manager2.get("complex_data")["numbers"] == [1, 2, 3]
        
        # Statistics might be loaded too (depending on implementation)
        info = manager2.get_info()
        assert info["initialized"] is True