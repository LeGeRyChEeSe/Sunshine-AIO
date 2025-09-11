"""
Library Downloader for Sunshine-AIO Community Library Integration

This module provides specialized downloading capabilities for community library tools,
including progress tracking, integrity verification, and error handling.
"""

import os
import json
import hashlib
import requests
import threading
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from urllib.parse import urlparse, urljoin
from datetime import datetime
import tempfile
import shutil

from misc.Logger import log_info, log_error, log_warning, log_success, log_progress
from .tool_provider import ToolInfo, ToolStatus


class DownloadProgress:
    """Track download progress and statistics."""
    
    def __init__(self, total_size: int = 0):
        self.total_size = total_size
        self.downloaded_size = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.last_downloaded_size = 0
        self.speed = 0.0
        self.eta = 0.0
        self._lock = threading.Lock()
    
    def update(self, chunk_size: int) -> None:
        """Update progress with new chunk size."""
        with self._lock:
            self.downloaded_size += chunk_size
            current_time = time.time()
            
            # Calculate speed (bytes per second)
            time_diff = current_time - self.last_update_time
            if time_diff >= 0.5:  # Update speed every 0.5 seconds
                size_diff = self.downloaded_size - self.last_downloaded_size
                self.speed = size_diff / time_diff if time_diff > 0 else 0
                self.last_update_time = current_time
                self.last_downloaded_size = self.downloaded_size
                
                # Calculate ETA
                if self.speed > 0 and self.total_size > 0:
                    remaining_size = self.total_size - self.downloaded_size
                    self.eta = remaining_size / self.speed
    
    def get_progress_percentage(self) -> float:
        """Get download progress as percentage."""
        if self.total_size <= 0:
            return 0.0
        return min(100.0, (self.downloaded_size / self.total_size) * 100)
    
    def get_speed_str(self) -> str:
        """Get human-readable speed string."""
        if self.speed < 1024:
            return f"{self.speed:.1f} B/s"
        elif self.speed < 1024 * 1024:
            return f"{self.speed / 1024:.1f} KB/s"
        else:
            return f"{self.speed / (1024 * 1024):.1f} MB/s"
    
    def get_eta_str(self) -> str:
        """Get human-readable ETA string."""
        if self.eta <= 0:
            return "Unknown"
        
        if self.eta < 60:
            return f"{int(self.eta)}s"
        elif self.eta < 3600:
            return f"{int(self.eta // 60)}m {int(self.eta % 60)}s"
        else:
            hours = int(self.eta // 3600)
            minutes = int((self.eta % 3600) // 60)
            return f"{hours}h {minutes}m"


class LibraryDownloader:
    """Download manager for community library tools."""
    
    def __init__(self, cache_dir: str, temp_dir: str = None):
        """
        Initialize the library downloader.
        
        Args:
            cache_dir: Directory for caching downloaded files
            temp_dir: Temporary directory for downloads (defaults to system temp)
        """
        self.cache_dir = cache_dir
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Sunshine-AIO/1.0 (Community Library Downloader)'
        })
        
        # Download configuration
        self.chunk_size = 8192  # 8KB chunks
        self.timeout = 30
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Progress tracking
        self._progress_callbacks: List[Callable[[DownloadProgress], None]] = []
        self._active_downloads: Dict[str, DownloadProgress] = {}
        self._download_lock = threading.Lock()
        
        # Ensure directories exist
        self._ensure_directories()
        
        log_info(f"LibraryDownloader initialized with cache: {self.cache_dir}")
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create directories: {e}")
            raise
    
    def add_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Add a progress callback function."""
        if callback not in self._progress_callbacks:
            self._progress_callbacks.append(callback)
    
    def remove_progress_callback(self, callback: Callable[[DownloadProgress], None]) -> None:
        """Remove a progress callback function."""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)
    
    def get_download_progress_callback(self) -> Callable[[DownloadProgress], None]:
        """
        Get a default progress callback for logging.
        
        Returns:
            Callable that logs download progress
        """
        def default_progress_callback(progress: DownloadProgress) -> None:
            percentage = progress.get_progress_percentage()
            speed = progress.get_speed_str()
            eta = progress.get_eta_str()
            
            if progress.total_size > 0:
                size_str = f"{progress.downloaded_size // 1024}KB/{progress.total_size // 1024}KB"
            else:
                size_str = f"{progress.downloaded_size // 1024}KB"
            
            log_progress(f"Downloading: {percentage:.1f}% ({size_str}) - {speed} - ETA: {eta}")
        
        return default_progress_callback
    
    def download_tool_metadata(self, tool_id: str, metadata_url: str = None) -> Optional[Dict[str, Any]]:
        """
        Download and parse tool metadata.
        
        Args:
            tool_id: ID of the tool
            metadata_url: URL to tool metadata (optional)
            
        Returns:
            Dict containing tool metadata or None on failure
        """
        try:
            log_info(f"Downloading metadata for tool: {tool_id}")
            
            if not metadata_url:
                # Construct default metadata URL pattern
                metadata_url = f"https://api.github.com/repos/LeGeRyChEeSe/sunshine-aio-library/contents/{tool_id}/metadata.json"
            
            response = self.session.get(metadata_url, timeout=self.timeout)
            response.raise_for_status()
            
            # GitHub API returns base64 encoded content
            if 'content' in response.json():
                import base64
                content = base64.b64decode(response.json()['content']).decode('utf-8')
                metadata = json.loads(content)
            else:
                metadata = response.json()
            
            log_success(f"Retrieved metadata for tool: {tool_id}")
            return metadata
            
        except requests.RequestException as e:
            log_error(f"Network error downloading metadata for {tool_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"JSON decode error for {tool_id} metadata: {e}")
            return None
        except Exception as e:
            log_error(f"Unexpected error downloading metadata for {tool_id}: {e}")
            return None
    
    def download_tool_files(self, tool_info: ToolInfo, destination: str = None) -> Optional[str]:
        """
        Download tool files with progress tracking and verification.
        
        Args:
            tool_info: ToolInfo object containing download information
            destination: Destination directory (defaults to cache_dir)
            
        Returns:
            Path to downloaded file or None on failure
        """
        if not tool_info.download_url:
            log_error(f"No download URL available for tool: {tool_info.tool_id}")
            return None
        
        destination = destination or self.cache_dir
        
        try:
            log_info(f"Starting download of tool: {tool_info.name}")
            
            # Determine file name from URL or metadata
            file_name = self._get_download_filename(tool_info)
            temp_file_path = os.path.join(self.temp_dir, f"{tool_info.tool_id}_{file_name}")
            final_file_path = os.path.join(destination, file_name)
            
            # Check if file already exists and is valid
            if os.path.exists(final_file_path):
                if self.verify_tool_integrity(tool_info, final_file_path):
                    log_info(f"Tool file already exists and is valid: {final_file_path}")
                    return final_file_path
                else:
                    log_warning(f"Existing file is corrupted, re-downloading: {final_file_path}")
            
            # Download with retries
            for attempt in range(self.max_retries):
                try:
                    success = self._download_file_with_progress(
                        tool_info.download_url,
                        temp_file_path,
                        tool_info.tool_id
                    )
                    
                    if success:
                        # Verify integrity
                        if self.verify_tool_integrity(tool_info, temp_file_path):
                            # Move to final location
                            os.makedirs(os.path.dirname(final_file_path), exist_ok=True)
                            shutil.move(temp_file_path, final_file_path)
                            log_success(f"Successfully downloaded: {final_file_path}")
                            return final_file_path
                        else:
                            log_error(f"Downloaded file failed integrity check: {tool_info.tool_id}")
                            if os.path.exists(temp_file_path):
                                os.remove(temp_file_path)
                    
                except Exception as e:
                    log_warning(f"Download attempt {attempt + 1} failed for {tool_info.tool_id}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    
                    # Clean up failed download
                    if os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except:
                            pass
            
            log_error(f"Failed to download tool after {self.max_retries} attempts: {tool_info.tool_id}")
            return None
            
        except Exception as e:
            log_error(f"Unexpected error downloading tool {tool_info.tool_id}: {e}")
            return None
        finally:
            # Clean up progress tracking
            with self._download_lock:
                if tool_info.tool_id in self._active_downloads:
                    del self._active_downloads[tool_info.tool_id]
    
    def _get_download_filename(self, tool_info: ToolInfo) -> str:
        """
        Determine the filename for download.
        
        Args:
            tool_info: ToolInfo object
            
        Returns:
            Filename for the download
        """
        if tool_info.download_url:
            # Extract filename from URL
            parsed_url = urlparse(tool_info.download_url)
            filename = os.path.basename(parsed_url.path)
            
            if filename and '.' in filename:
                return filename
        
        # Default filename
        return f"{tool_info.tool_id}_v{tool_info.version}.zip"
    
    def _download_file_with_progress(self, url: str, file_path: str, tool_id: str) -> bool:
        """
        Download file with progress tracking.
        
        Args:
            url: URL to download from
            file_path: Local file path to save to
            tool_id: Tool ID for progress tracking
            
        Returns:
            True if download was successful
        """
        try:
            # Start download with stream=True
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Get file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Initialize progress tracking
            progress = DownloadProgress(total_size)
            with self._download_lock:
                self._active_downloads[tool_id] = progress
            
            # Download file in chunks
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        file.write(chunk)
                        progress.update(len(chunk))
                        
                        # Notify callbacks
                        for callback in self._progress_callbacks:
                            try:
                                callback(progress)
                            except Exception as e:
                                log_warning(f"Progress callback error: {e}")
            
            log_success(f"Download completed: {file_path}")
            return True
            
        except requests.RequestException as e:
            log_error(f"Network error downloading from {url}: {e}")
            return False
        except IOError as e:
            log_error(f"File I/O error: {e}")
            return False
        except Exception as e:
            log_error(f"Unexpected error downloading file: {e}")
            return False
    
    def verify_tool_integrity(self, tool_info: ToolInfo, file_path: str) -> bool:
        """
        Verify the integrity of a downloaded tool file.
        
        Args:
            tool_info: ToolInfo object containing checksum information
            file_path: Path to the downloaded file
            
        Returns:
            True if file integrity is verified
        """
        if not os.path.exists(file_path):
            log_error(f"File does not exist for verification: {file_path}")
            return False
        
        try:
            # Basic file size check
            file_size = os.path.getsize(file_path)
            if hasattr(tool_info, 'size') and tool_info.size > 0:
                if abs(file_size - tool_info.size) > (tool_info.size * 0.05):  # 5% tolerance
                    log_warning(f"File size mismatch for {tool_info.tool_id}: expected {tool_info.size}, got {file_size}")
            
            # Checksum verification
            if hasattr(tool_info, 'checksum') and tool_info.checksum:
                calculated_checksum = self._calculate_file_checksum(file_path)
                expected_checksum = tool_info.checksum.lower()
                
                if calculated_checksum != expected_checksum:
                    log_error(f"Checksum mismatch for {tool_info.tool_id}: expected {expected_checksum}, got {calculated_checksum}")
                    return False
                
                log_info(f"Checksum verified for {tool_info.tool_id}")
            else:
                log_info(f"No checksum available for {tool_info.tool_id}, skipping verification")
            
            # Additional file format validation
            if not self._validate_file_format(file_path, tool_info):
                return False
            
            log_success(f"File integrity verified: {file_path}")
            return True
            
        except Exception as e:
            log_error(f"Error verifying file integrity: {e}")
            return False
    
    def _calculate_file_checksum(self, file_path: str, algorithm: str = 'sha256') -> str:
        """
        Calculate checksum for a file.
        
        Args:
            file_path: Path to the file
            algorithm: Hashing algorithm to use
            
        Returns:
            Hexadecimal checksum string
        """
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as file:
            while chunk := file.read(self.chunk_size):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest().lower()
    
    def _validate_file_format(self, file_path: str, tool_info: ToolInfo) -> bool:
        """
        Validate file format based on extension and magic bytes.
        
        Args:
            file_path: Path to the file
            tool_info: ToolInfo object
            
        Returns:
            True if file format is valid
        """
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Read magic bytes
            with open(file_path, 'rb') as file:
                magic_bytes = file.read(8)
            
            # Basic format validation
            if file_extension == '.zip':
                # ZIP file magic bytes: PK
                if not magic_bytes.startswith(b'PK'):
                    log_error(f"Invalid ZIP file format: {file_path}")
                    return False
            elif file_extension == '.exe':
                # Windows PE magic bytes: MZ
                if not magic_bytes.startswith(b'MZ'):
                    log_error(f"Invalid EXE file format: {file_path}")
                    return False
            elif file_extension == '.msi':
                # MSI files start with specific signature
                if not magic_bytes.startswith(b'\xd0\xcf\x11\xe0'):
                    log_error(f"Invalid MSI file format: {file_path}")
                    return False
            
            return True
            
        except Exception as e:
            log_warning(f"File format validation error: {e}")
            return True  # Don't fail on validation errors
    
    def get_download_status(self, tool_id: str) -> Optional[DownloadProgress]:
        """
        Get download progress for a specific tool.
        
        Args:
            tool_id: ID of the tool
            
        Returns:
            DownloadProgress object or None if not downloading
        """
        with self._download_lock:
            return self._active_downloads.get(tool_id)
    
    def cancel_download(self, tool_id: str) -> bool:
        """
        Cancel an active download (placeholder for future implementation).
        
        Args:
            tool_id: ID of the tool to cancel
            
        Returns:
            True if download was cancelled
        """
        # TODO: Implement download cancellation
        log_warning(f"Download cancellation not yet implemented for: {tool_id}")
        return False
    
    def clear_cache(self, tool_id: str = None) -> bool:
        """
        Clear download cache for specific tool or all tools.
        
        Args:
            tool_id: Specific tool ID to clear (None for all)
            
        Returns:
            True if cache was cleared successfully
        """
        try:
            if tool_id:
                # Clear specific tool cache
                pattern = f"{tool_id}_*"
                import glob
                files = glob.glob(os.path.join(self.cache_dir, pattern))
                for file_path in files:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        log_info(f"Removed cached file: {file_path}")
            else:
                # Clear all cache
                if os.path.exists(self.cache_dir):
                    shutil.rmtree(self.cache_dir)
                    os.makedirs(self.cache_dir, exist_ok=True)
                    log_info("Cleared all download cache")
            
            return True
            
        except Exception as e:
            log_error(f"Error clearing cache: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get information about the download cache.
        
        Returns:
            Dict containing cache information
        """
        try:
            cache_size = 0
            file_count = 0
            
            if os.path.exists(self.cache_dir):
                for root, dirs, files in os.walk(self.cache_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.isfile(file_path):
                            cache_size += os.path.getsize(file_path)
                            file_count += 1
            
            return {
                'cache_dir': self.cache_dir,
                'total_size_bytes': cache_size,
                'total_size_mb': cache_size / (1024 * 1024),
                'file_count': file_count,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(f"Error getting cache info: {e}")
            return {
                'cache_dir': self.cache_dir,
                'error': str(e)
            }