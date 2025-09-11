"""
Cache Manager for Sunshine-AIO Library Integration

This module provides comprehensive caching functionality for library metadata,
tool information, and downloaded content with expiration handling and cleanup.
"""

import os
import json
import time
import hashlib
import threading
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import shutil

from misc.Logger import log_info, log_error, log_warning, log_success


class CacheEntry:
    """
    Represents a single cache entry with metadata and expiration handling.
    """
    
    def __init__(self, key: str, data: Any, ttl: int = 3600, created_at: datetime = None):
        """
        Initialize a cache entry.
        
        Args:
            key: Unique identifier for the cache entry
            data: The data to cache
            ttl: Time to live in seconds
            created_at: Creation timestamp (defaults to now)
        """
        self.key = key
        self.data = data
        self.ttl = ttl
        self.created_at = created_at or datetime.now()
        self.expires_at = self.created_at + timedelta(seconds=ttl)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return datetime.now() > self.expires_at
    
    def refresh(self, ttl: int = None) -> None:
        """
        Refresh the expiration time of this entry.
        
        Args:
            ttl: New time to live (uses original TTL if not provided)
        """
        if ttl is None:
            ttl = self.ttl
        
        self.ttl = ttl
        self.expires_at = datetime.now() + timedelta(seconds=ttl)
    
    def access(self) -> Any:
        """
        Access the cached data and update access statistics.
        
        Returns:
            The cached data
        """
        self.access_count += 1
        self.last_accessed = datetime.now()
        return self.data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary for serialization."""
        return {
            'key': self.key,
            'data': self.data,
            'ttl': self.ttl,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Create cache entry from dictionary."""
        entry = cls(
            key=data['key'],
            data=data['data'],
            ttl=data['ttl'],
            created_at=datetime.fromisoformat(data['created_at'])
        )
        entry.expires_at = datetime.fromisoformat(data['expires_at'])
        entry.access_count = data.get('access_count', 0)
        entry.last_accessed = datetime.fromisoformat(
            data.get('last_accessed', data['created_at'])
        )
        return entry


class CacheManager:
    """
    Advanced cache manager for local metadata storage and file caching.
    
    Features:
    - JSON-based metadata storage with expiration
    - File-based caching for downloaded content
    - Automatic cleanup of expired entries
    - Thread-safe operations
    - Cache statistics and monitoring
    - Configurable storage limits
    """
    
    def __init__(self, cache_dir: str, config: Dict[str, Any] = None):
        """
        Initialize the cache manager.
        
        Args:
            cache_dir: Directory for cache storage
            config: Configuration dictionary
        """
        self.cache_dir = os.path.abspath(cache_dir)
        self.metadata_dir = os.path.join(self.cache_dir, "metadata")
        self.files_dir = os.path.join(self.cache_dir, "files")
        self.temp_dir = os.path.join(self.cache_dir, "temp")
        
        # Configuration with defaults
        self.config = {
            'default_ttl': 3600,           # 1 hour
            'max_cache_size': 1024 * 1024 * 1024,  # 1GB
            'max_entries': 10000,          # Maximum cache entries
            'cleanup_interval': 3600,       # 1 hour
            'auto_cleanup': True,          # Automatic cleanup enabled
            'compression_enabled': False,   # Compression for large files
            'checksum_validation': True     # Validate file checksums
        }
        
        if config:
            self.config.update(config)
        
        # Internal state
        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_size': 0,
            'last_cleanup': None
        }
        
        # Initialize cache directory structure
        self._initialize_directories()
        
        # Load existing cache
        self._load_cache()
        
        log_info(f"CacheManager initialized: {self.cache_dir}")
    
    def _initialize_directories(self) -> None:
        """Create necessary cache directories."""
        try:
            for directory in [self.cache_dir, self.metadata_dir, self.files_dir, self.temp_dir]:
                os.makedirs(directory, exist_ok=True)
            
            log_info("Cache directories initialized")
            
        except OSError as e:
            log_error(f"Failed to initialize cache directories: {e}")
            raise
    
    def _load_cache(self) -> None:
        """Load cache entries from persistent storage."""
        cache_index_file = os.path.join(self.metadata_dir, "cache_index.json")
        
        try:
            if os.path.exists(cache_index_file):
                with open(cache_index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                loaded_count = 0
                expired_count = 0
                
                for entry_data in index_data.get('entries', []):
                    try:
                        entry = CacheEntry.from_dict(entry_data)
                        
                        if entry.is_expired():
                            expired_count += 1
                            continue
                        
                        self._cache[entry.key] = entry
                        loaded_count += 1
                        
                    except Exception as e:
                        log_warning(f"Failed to load cache entry: {e}")
                
                # Update stats
                if 'stats' in index_data:
                    self._stats.update(index_data['stats'])
                
                log_info(f"Loaded {loaded_count} cache entries, {expired_count} expired")
                
                # Clean up expired entries if auto cleanup is enabled
                if self.config['auto_cleanup'] and expired_count > 0:
                    self._cleanup_expired()
            else:
                log_info("No existing cache index found")
                
        except Exception as e:
            log_error(f"Failed to load cache: {e}")
            self._cache = {}
    
    def _save_cache(self) -> None:
        """Save cache entries to persistent storage."""
        cache_index_file = os.path.join(self.metadata_dir, "cache_index.json")
        
        try:
            with self._cache_lock:
                index_data = {
                    'version': '1.0',
                    'created_at': datetime.now().isoformat(),
                    'entries': [entry.to_dict() for entry in self._cache.values()],
                    'stats': self._stats.copy()
                }
            
            # Write to temporary file first
            temp_file = cache_index_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_file, cache_index_file)
            
            log_info(f"Cache saved: {len(self._cache)} entries")
            
        except Exception as e:
            log_error(f"Failed to save cache: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats['misses'] += 1
                return default
            
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                return default
            
            self._stats['hits'] += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not provided)
            
        Returns:
            bool: True if successfully cached
        """
        if ttl is None:
            ttl = self.config['default_ttl']
        
        try:
            with self._cache_lock:
                entry = CacheEntry(key, value, ttl)
                self._cache[key] = entry
                
                # Check if we need to evict entries
                if len(self._cache) > self.config['max_entries']:
                    self._evict_lru()
            
            log_info(f"Cached entry: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            log_error(f"Failed to cache entry {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a cache entry.
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if entry was deleted
        """
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                log_info(f"Deleted cache entry: {key}")
                return True
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache and is not expired.
        
        Args:
            key: Cache key to check
            
        Returns:
            bool: True if key exists and is valid
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            return entry is not None and not entry.is_expired()
    
    def refresh(self, key: str, ttl: int = None) -> bool:
        """
        Refresh the expiration time of a cache entry.
        
        Args:
            key: Cache key to refresh
            ttl: New time to live (uses original TTL if not provided)
            
        Returns:
            bool: True if entry was refreshed
        """
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry:
                entry.refresh(ttl)
                log_info(f"Refreshed cache entry: {key}")
                return True
            return False
    
    def cache_file(self, file_path: str, content: bytes, key: str = None, 
                   checksum: str = None, ttl: int = None) -> str:
        """
        Cache a file to the file cache.
        
        Args:
            file_path: Original file path (for generating cache key)
            content: File content as bytes
            key: Custom cache key (auto-generated if not provided)
            checksum: Expected checksum for validation
            ttl: Time to live for metadata
            
        Returns:
            str: Path to cached file
        """
        if key is None:
            key = self._generate_file_key(file_path)
        
        try:
            # Generate cached file path
            cache_file_path = os.path.join(self.files_dir, f"{key}.cache")
            
            # Write file content
            with open(cache_file_path, 'wb') as f:
                f.write(content)
            
            # Calculate checksum if validation is enabled
            if self.config['checksum_validation']:
                calculated_checksum = hashlib.sha256(content).hexdigest()
                
                if checksum and calculated_checksum != checksum:
                    os.remove(cache_file_path)
                    raise ValueError(f"Checksum mismatch for {file_path}")
                
                checksum = calculated_checksum
            
            # Cache metadata
            metadata = {
                'original_path': file_path,
                'cache_path': cache_file_path,
                'size': len(content),
                'checksum': checksum,
                'cached_at': datetime.now().isoformat()
            }
            
            self.set(f"file:{key}", metadata, ttl)
            
            # Update stats
            self._stats['total_size'] += len(content)
            
            log_info(f"Cached file: {file_path} -> {cache_file_path}")
            return cache_file_path
            
        except Exception as e:
            log_error(f"Failed to cache file {file_path}: {e}")
            raise
    
    def get_cached_file(self, key: str) -> Optional[str]:
        """
        Get path to a cached file.
        
        Args:
            key: File cache key
            
        Returns:
            Path to cached file or None if not found
        """
        metadata = self.get(f"file:{key}")
        
        if metadata is None:
            return None
        
        cache_path = metadata.get('cache_path')
        
        if cache_path and os.path.exists(cache_path):
            # Validate checksum if enabled
            if self.config['checksum_validation'] and metadata.get('checksum'):
                try:
                    with open(cache_path, 'rb') as f:
                        content = f.read()
                    
                    calculated_checksum = hashlib.sha256(content).hexdigest()
                    expected_checksum = metadata['checksum']
                    
                    if calculated_checksum != expected_checksum:
                        log_warning(f"Checksum mismatch for cached file: {cache_path}")
                        self.delete_cached_file(key)
                        return None
                        
                except Exception as e:
                    log_error(f"Error validating cached file {cache_path}: {e}")
                    return None
            
            return cache_path
        
        # File doesn't exist, clean up metadata
        self.delete(f"file:{key}")
        return None
    
    def delete_cached_file(self, key: str) -> bool:
        """
        Delete a cached file and its metadata.
        
        Args:
            key: File cache key
            
        Returns:
            bool: True if file was deleted
        """
        try:
            metadata = self.get(f"file:{key}")
            
            if metadata:
                cache_path = metadata.get('cache_path')
                if cache_path and os.path.exists(cache_path):
                    os.remove(cache_path)
                    self._stats['total_size'] -= metadata.get('size', 0)
                
                self.delete(f"file:{key}")
            
            log_info(f"Deleted cached file: {key}")
            return True
            
        except Exception as e:
            log_error(f"Failed to delete cached file {key}: {e}")
            return False
    
    def _generate_file_key(self, file_path: str) -> str:
        """Generate a cache key for a file path."""
        return hashlib.md5(file_path.encode('utf-8')).hexdigest()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries to stay within limits."""
        if len(self._cache) <= self.config['max_entries']:
            return
        
        # Sort entries by last accessed time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest entries
        entries_to_remove = len(self._cache) - self.config['max_entries']
        
        for i in range(entries_to_remove):
            key, entry = sorted_entries[i]
            
            # Clean up file cache if it's a file entry
            if key.startswith('file:'):
                file_key = key[5:]  # Remove 'file:' prefix
                self.delete_cached_file(file_key)
            else:
                del self._cache[key]
            
            self._stats['evictions'] += 1
        
        log_info(f"Evicted {entries_to_remove} LRU cache entries")
    
    def _cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            int: Number of entries cleaned up
        """
        with self._cache_lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            cleaned_count = 0
            for key in expired_keys:
                if key.startswith('file:'):
                    file_key = key[5:]  # Remove 'file:' prefix
                    if self.delete_cached_file(file_key):
                        cleaned_count += 1
                else:
                    if self.delete(key):
                        cleaned_count += 1
            
            if cleaned_count > 0:
                log_info(f"Cleaned up {cleaned_count} expired cache entries")
            
            self._stats['last_cleanup'] = datetime.now().isoformat()
            return cleaned_count
    
    def cleanup(self, force: bool = False) -> Dict[str, int]:
        """
        Perform cache cleanup.
        
        Args:
            force: Force cleanup regardless of interval
            
        Returns:
            Dict with cleanup statistics
        """
        last_cleanup = self._stats.get('last_cleanup')
        
        if not force and last_cleanup:
            last_cleanup_time = datetime.fromisoformat(last_cleanup)
            time_since_cleanup = datetime.now() - last_cleanup_time
            
            if time_since_cleanup.total_seconds() < self.config['cleanup_interval']:
                return {'skipped': True, 'reason': 'cleanup_interval_not_reached'}
        
        log_info("Starting cache cleanup...")
        
        expired_cleaned = self._cleanup_expired()
        
        # Check cache size and evict if necessary
        evicted = 0
        if len(self._cache) > self.config['max_entries']:
            old_count = len(self._cache)
            self._evict_lru()
            evicted = old_count - len(self._cache)
        
        # Clean up orphaned files
        orphaned_cleaned = self._cleanup_orphaned_files()
        
        return {
            'expired_cleaned': expired_cleaned,
            'evicted': evicted,
            'orphaned_cleaned': orphaned_cleaned,
            'total_entries': len(self._cache)
        }
    
    def _cleanup_orphaned_files(self) -> int:
        """
        Clean up files that exist in the file cache but have no metadata.
        
        Returns:
            int: Number of orphaned files cleaned up
        """
        try:
            if not os.path.exists(self.files_dir):
                return 0
            
            # Get all cached file keys from metadata
            valid_keys = set()
            for key in self._cache.keys():
                if key.startswith('file:'):
                    file_key = key[5:]  # Remove 'file:' prefix
                    valid_keys.add(f"{file_key}.cache")
            
            # Check all files in the cache directory
            orphaned_count = 0
            for filename in os.listdir(self.files_dir):
                if filename.endswith('.cache') and filename not in valid_keys:
                    file_path = os.path.join(self.files_dir, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        self._stats['total_size'] -= file_size
                        orphaned_count += 1
                    except Exception as e:
                        log_warning(f"Failed to remove orphaned file {filename}: {e}")
            
            if orphaned_count > 0:
                log_info(f"Cleaned up {orphaned_count} orphaned cache files")
            
            return orphaned_count
            
        except Exception as e:
            log_error(f"Error cleaning up orphaned files: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict containing cache statistics
        """
        with self._cache_lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            
            stats = self._stats.copy()
            stats.update({
                'total_entries': total_entries,
                'expired_entries': expired_entries,
                'hit_rate': stats['hits'] / (stats['hits'] + stats['misses']) if (stats['hits'] + stats['misses']) > 0 else 0,
                'cache_dir': self.cache_dir,
                'config': self.config.copy()
            })
            
            return stats
    
    def clear(self, include_files: bool = True) -> bool:
        """
        Clear all cache entries.
        
        Args:
            include_files: Whether to also clear cached files
            
        Returns:
            bool: True if cache was cleared successfully
        """
        try:
            with self._cache_lock:
                if include_files:
                    # Remove all cached files
                    if os.path.exists(self.files_dir):
                        shutil.rmtree(self.files_dir)
                        os.makedirs(self.files_dir, exist_ok=True)
                
                # Clear in-memory cache
                self._cache.clear()
                
                # Reset stats
                self._stats = {
                    'hits': 0,
                    'misses': 0,
                    'evictions': 0,
                    'total_size': 0,
                    'last_cleanup': datetime.now().isoformat()
                }
            
            log_success("Cache cleared successfully")
            return True
            
        except Exception as e:
            log_error(f"Failed to clear cache: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save the current cache state to disk.
        
        Returns:
            bool: True if save was successful
        """
        try:
            self._save_cache()
            return True
        except Exception as e:
            log_error(f"Failed to save cache: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - save cache state."""
        self.save()


def get_cache_manager(cache_dir: str, config: Dict[str, Any] = None) -> CacheManager:
    """
    Factory function to get a CacheManager instance.
    
    Args:
        cache_dir: Directory for cache storage
        config: Configuration dictionary
        
    Returns:
        CacheManager: Configured CacheManager instance
    """
    return CacheManager(cache_dir, config)