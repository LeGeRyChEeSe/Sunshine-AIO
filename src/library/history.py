"""
Installation History and Analytics for Sunshine-AIO Community Library

This module provides comprehensive tracking of installation history, usage analytics,
and insights into user behavior patterns with tools from the community library.
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading

from misc.Logger import log_info, log_error, log_warning, log_success


class InstallationHistory:
    """
    Track and analyze installation history with comprehensive analytics
    and reporting capabilities for community library tools.
    """
    
    def __init__(self, base_path: str):
        """
        Initialize the installation history tracker.
        
        Args:
            base_path: Base path for storing history data
        """
        self.base_path = base_path
        self.history_dir = os.path.join(base_path, "user_data", "library", "history")
        self.history_file = os.path.join(self.history_dir, "installation_history.json")
        self.analytics_file = os.path.join(self.history_dir, "analytics_cache.json")
        
        # In-memory storage
        self._history: List[Dict[str, Any]] = []
        self._analytics_cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Configuration
        self.max_history_entries = 1000
        self.analytics_cache_duration = 3600  # 1 hour in seconds
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing data
        self._load_history()
        self._load_analytics_cache()
        
        log_info("InstallationHistory initialized")
    
    def record_installation(self, tool_id: str, success: bool, details: dict) -> None:
        """
        Record a tool installation attempt.
        
        Args:
            tool_id: ID of the tool that was installed
            success: Whether the installation was successful
            details: Additional details about the installation
                    Expected keys:
                    - duration: Installation duration in seconds
                    - install_path: Path where tool was installed
                    - version: Version of the tool installed
                    - size: Size of installed files
                    - method: Installation method used
                    - error_message: Error message if failed
                    - user_initiated: Whether user manually initiated
        """
        try:
            with self._lock:
                timestamp = datetime.now()
                
                history_entry = {
                    'id': self._generate_entry_id(),
                    'timestamp': timestamp.isoformat(),
                    'action': 'installation',
                    'tool_id': tool_id,
                    'success': success,
                    'details': details.copy()
                }
                
                # Add computed fields
                history_entry['details']['recorded_at'] = timestamp.isoformat()
                history_entry['details']['day_of_week'] = timestamp.strftime('%A')
                history_entry['details']['hour'] = timestamp.hour
                
                self._history.append(history_entry)
                
                # Maintain history size limit
                if len(self._history) > self.max_history_entries:
                    self._history = self._history[-self.max_history_entries:]
                
                # Save to file
                self._save_history()
                
                # Update analytics cache
                self._invalidate_analytics_cache()
                
                status = "successful" if success else "failed"
                log_info(f"Recorded {status} installation of {tool_id}")
                
        except Exception as e:
            log_error(f"Error recording installation: {e}")
    
    def record_uninstallation(self, tool_id: str, details: dict) -> None:
        """
        Record a tool uninstallation.
        
        Args:
            tool_id: ID of the tool that was uninstalled
            details: Additional details about the uninstallation
                    Expected keys:
                    - duration: Uninstallation duration in seconds
                    - method: Uninstallation method used
                    - files_removed: Number of files removed
                    - cleanup_successful: Whether cleanup was complete
                    - user_initiated: Whether user manually initiated
        """
        try:
            with self._lock:
                timestamp = datetime.now()
                
                history_entry = {
                    'id': self._generate_entry_id(),
                    'timestamp': timestamp.isoformat(),
                    'action': 'uninstallation',
                    'tool_id': tool_id,
                    'success': True,  # Assume successful unless specified
                    'details': details.copy()
                }
                
                # Add computed fields
                history_entry['details']['recorded_at'] = timestamp.isoformat()
                history_entry['details']['day_of_week'] = timestamp.strftime('%A')
                history_entry['details']['hour'] = timestamp.hour
                
                self._history.append(history_entry)
                
                # Maintain history size limit
                if len(self._history) > self.max_history_entries:
                    self._history = self._history[-self.max_history_entries:]
                
                # Save to file
                self._save_history()
                
                # Update analytics cache
                self._invalidate_analytics_cache()
                
                log_info(f"Recorded uninstallation of {tool_id}")
                
        except Exception as e:
            log_error(f"Error recording uninstallation: {e}")
    
    def get_installation_history(self, limit: int = 50) -> List[dict]:
        """
        Get recent installation history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries, most recent first
        """
        try:
            with self._lock:
                # Return most recent entries
                return list(reversed(self._history[-limit:]))
                
        except Exception as e:
            log_error(f"Error getting installation history: {e}")
            return []
    
    def get_popular_tools(self, limit: int = 10, time_period_days: int = 30) -> List[str]:
        """
        Get most popular tools based on installation frequency.
        
        Args:
            limit: Maximum number of tools to return
            time_period_days: Time period to analyze (in days)
            
        Returns:
            List of tool IDs sorted by popularity (most popular first)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=time_period_days)
            
            tool_installs = Counter()
            
            with self._lock:
                for entry in self._history:
                    if entry['action'] != 'installation' or not entry['success']:
                        continue
                    
                    entry_date = self._parse_timestamp(entry['timestamp'])
                    if entry_date >= cutoff_date:
                        tool_installs[entry['tool_id']] += 1
            
            # Get most common tools
            popular_tools = [tool_id for tool_id, _ in tool_installs.most_common(limit)]
            
            log_info(f"Retrieved {len(popular_tools)} popular tools from last {time_period_days} days")
            return popular_tools
            
        except Exception as e:
            log_error(f"Error getting popular tools: {e}")
            return []
    
    def get_success_rate(self, tool_id: str = None, time_period_days: int = 30) -> float:
        """
        Get installation success rate.
        
        Args:
            tool_id: Specific tool ID to analyze (None for overall rate)
            time_period_days: Time period to analyze (in days)
            
        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=time_period_days)
            
            total_installations = 0
            successful_installations = 0
            
            with self._lock:
                for entry in self._history:
                    if entry['action'] != 'installation':
                        continue
                    
                    if tool_id and entry['tool_id'] != tool_id:
                        continue
                    
                    entry_date = self._parse_timestamp(entry['timestamp'])
                    if entry_date >= cutoff_date:
                        total_installations += 1
                        if entry['success']:
                            successful_installations += 1
            
            if total_installations == 0:
                return 0.0
            
            success_rate = successful_installations / total_installations
            
            target = f"tool {tool_id}" if tool_id else "overall"
            log_info(f"Success rate for {target}: {success_rate:.2%}")
            
            return success_rate
            
        except Exception as e:
            log_error(f"Error calculating success rate: {e}")
            return 0.0
    
    def generate_usage_report(self) -> dict:
        """
        Generate comprehensive usage report with analytics.
        
        Returns:
            Dictionary containing detailed usage statistics
        """
        try:
            # Check analytics cache first
            cache_key = "usage_report"
            cached_report = self._get_cached_analytics(cache_key)
            if cached_report:
                log_info("Returning cached usage report")
                return cached_report
            
            with self._lock:
                report = {
                    'generated_at': datetime.now().isoformat(),
                    'total_entries': len(self._history),
                    'summary': self._generate_summary_stats(),
                    'trends': self._generate_trend_analysis(),
                    'tool_analytics': self._generate_tool_analytics(),
                    'time_analytics': self._generate_time_analytics(),
                    'performance_metrics': self._generate_performance_metrics(),
                    'error_analysis': self._generate_error_analysis()
                }
            
            # Cache the report
            self._cache_analytics(cache_key, report)
            
            log_info("Generated comprehensive usage report")
            return report
            
        except Exception as e:
            log_error(f"Error generating usage report: {e}")
            return {
                'generated_at': datetime.now().isoformat(),
                'error': str(e),
                'total_entries': len(self._history)
            }
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Clean up old history records.
        
        Args:
            days: Number of days of history to keep
            
        Returns:
            Number of records removed
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self._lock:
                original_count = len(self._history)
                
                # Filter out old records
                self._history = [
                    entry for entry in self._history
                    if self._parse_timestamp(entry['timestamp']) >= cutoff_date
                ]
                
                removed_count = original_count - len(self._history)
                
                if removed_count > 0:
                    # Save updated history
                    self._save_history()
                    
                    # Invalidate analytics cache
                    self._invalidate_analytics_cache()
                    
                    log_success(f"Cleaned up {removed_count} old history records")
                else:
                    log_info("No old records to clean up")
                
                return removed_count
                
        except Exception as e:
            log_error(f"Error cleaning up old records: {e}")
            return 0
    
    def get_tool_usage_timeline(self, tool_id: str, time_period_days: int = 30) -> List[dict]:
        """
        Get usage timeline for a specific tool.
        
        Args:
            tool_id: Tool ID to analyze
            time_period_days: Time period to analyze
            
        Returns:
            List of usage events with timestamps
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=time_period_days)
            timeline = []
            
            with self._lock:
                for entry in self._history:
                    if entry['tool_id'] != tool_id:
                        continue
                    
                    entry_date = self._parse_timestamp(entry['timestamp'])
                    if entry_date >= cutoff_date:
                        timeline.append({
                            'timestamp': entry['timestamp'],
                            'action': entry['action'],
                            'success': entry['success'],
                            'details': entry.get('details', {})
                        })
            
            # Sort by timestamp (oldest first)
            timeline.sort(key=lambda x: x['timestamp'])
            
            log_info(f"Retrieved timeline for {tool_id}: {len(timeline)} events")
            return timeline
            
        except Exception as e:
            log_error(f"Error getting tool usage timeline: {e}")
            return []
    
    def export_history(self, file_path: str, format_type: str = 'json') -> bool:
        """
        Export history to a file.
        
        Args:
            file_path: Path to export file
            format_type: Export format ('json' or 'csv')
            
        Returns:
            True if export was successful
        """
        try:
            # Ensure export directory exists
            export_dir = os.path.dirname(file_path)
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)
            
            with self._lock:
                if format_type.lower() == 'json':
                    export_data = {
                        'exported_at': datetime.now().isoformat(),
                        'total_entries': len(self._history),
                        'history': self._history
                    }
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                elif format_type.lower() == 'csv':
                    import csv
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        if not self._history:
                            f.write("No history data to export\n")
                            return True
                        
                        # Prepare CSV data
                        fieldnames = ['timestamp', 'action', 'tool_id', 'success']
                        
                        # Add dynamic fields from details
                        detail_fields = set()
                        for entry in self._history:
                            detail_fields.update(entry.get('details', {}).keys())
                        
                        fieldnames.extend(sorted(detail_fields))
                        
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        
                        for entry in self._history:
                            row = {
                                'timestamp': entry['timestamp'],
                                'action': entry['action'],
                                'tool_id': entry['tool_id'],
                                'success': entry['success']
                            }
                            
                            # Add details fields
                            details = entry.get('details', {})
                            for field in detail_fields:
                                row[field] = details.get(field, '')
                            
                            writer.writerow(row)
                
                else:
                    log_error(f"Unsupported export format: {format_type}")
                    return False
            
            log_success(f"Exported history to {file_path} ({format_type} format)")
            return True
            
        except Exception as e:
            log_error(f"Error exporting history: {e}")
            return False
    
    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        try:
            os.makedirs(self.history_dir, exist_ok=True)
        except OSError as e:
            log_error(f"Failed to create history directory: {e}")
            raise
    
    def _load_history(self) -> None:
        """Load history from file."""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        self._history = data
                    elif isinstance(data, dict):
                        self._history = data.get('history', [])
                    
                log_info(f"Loaded {len(self._history)} history entries")
            else:
                log_info("No existing history file found")
                
        except Exception as e:
            log_error(f"Error loading history: {e}")
            self._history = []
    
    def _save_history(self) -> None:
        """Save history to file."""
        try:
            history_data = {
                'version': '1.0',
                'saved_at': datetime.now().isoformat(),
                'total_entries': len(self._history),
                'history': self._history
            }
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            log_error(f"Error saving history: {e}")
    
    def _load_analytics_cache(self) -> None:
        """Load analytics cache from file."""
        try:
            if os.path.exists(self.analytics_file):
                with open(self.analytics_file, 'r', encoding='utf-8') as f:
                    self._analytics_cache = json.load(f)
                
                log_info("Loaded analytics cache")
            else:
                self._analytics_cache = {}
                
        except Exception as e:
            log_error(f"Error loading analytics cache: {e}")
            self._analytics_cache = {}
    
    def _save_analytics_cache(self) -> None:
        """Save analytics cache to file."""
        try:
            with open(self.analytics_file, 'w', encoding='utf-8') as f:
                json.dump(self._analytics_cache, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            log_error(f"Error saving analytics cache: {e}")
    
    def _get_cached_analytics(self, cache_key: str) -> Optional[dict]:
        """Get cached analytics if still valid."""
        try:
            if cache_key not in self._analytics_cache:
                return None
            
            cached_entry = self._analytics_cache[cache_key]
            cached_time = self._parse_timestamp(cached_entry.get('cached_at', ''))
            
            # Check if cache is still valid
            if datetime.now() - cached_time < timedelta(seconds=self.analytics_cache_duration):
                return cached_entry.get('data')
            
            return None
            
        except Exception as e:
            log_error(f"Error getting cached analytics: {e}")
            return None
    
    def _cache_analytics(self, cache_key: str, data: dict) -> None:
        """Cache analytics data."""
        try:
            self._analytics_cache[cache_key] = {
                'cached_at': datetime.now().isoformat(),
                'data': data
            }
            
            # Save cache to file
            self._save_analytics_cache()
            
        except Exception as e:
            log_error(f"Error caching analytics: {e}")
    
    def _invalidate_analytics_cache(self) -> None:
        """Invalidate analytics cache."""
        try:
            self._analytics_cache.clear()
            self._save_analytics_cache()
            
        except Exception as e:
            log_error(f"Error invalidating analytics cache: {e}")
    
    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        try:
            import uuid
            return str(uuid.uuid4())[:8]
        except Exception:
            # Fallback to timestamp-based ID
            return datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime object."""
        try:
            if timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.min
        except Exception as e:
            log_error(f"Error parsing timestamp: {e}")
            return datetime.min
    
    def _generate_summary_stats(self) -> dict:
        """Generate summary statistics."""
        try:
            stats = {
                'total_installations': 0,
                'successful_installations': 0,
                'failed_installations': 0,
                'total_uninstallations': 0,
                'unique_tools': set(),
                'success_rate': 0.0
            }
            
            for entry in self._history:
                if entry['action'] == 'installation':
                    stats['total_installations'] += 1
                    if entry['success']:
                        stats['successful_installations'] += 1
                    else:
                        stats['failed_installations'] += 1
                elif entry['action'] == 'uninstallation':
                    stats['total_uninstallations'] += 1
                
                stats['unique_tools'].add(entry['tool_id'])
            
            # Calculate success rate
            if stats['total_installations'] > 0:
                stats['success_rate'] = stats['successful_installations'] / stats['total_installations']
            
            # Convert set to count
            stats['unique_tools'] = len(stats['unique_tools'])
            
            return stats
            
        except Exception as e:
            log_error(f"Error generating summary stats: {e}")
            return {}
    
    def _generate_trend_analysis(self) -> dict:
        """Generate trend analysis."""
        try:
            trends = {
                'daily_activity': defaultdict(int),
                'weekly_activity': defaultdict(int),
                'monthly_activity': defaultdict(int)
            }
            
            for entry in self._history:
                entry_date = self._parse_timestamp(entry['timestamp'])
                
                day_key = entry_date.strftime('%Y-%m-%d')
                week_key = entry_date.strftime('%Y-W%U')
                month_key = entry_date.strftime('%Y-%m')
                
                trends['daily_activity'][day_key] += 1
                trends['weekly_activity'][week_key] += 1
                trends['monthly_activity'][month_key] += 1
            
            # Convert defaultdict to regular dict
            return {
                'daily_activity': dict(trends['daily_activity']),
                'weekly_activity': dict(trends['weekly_activity']),
                'monthly_activity': dict(trends['monthly_activity'])
            }
            
        except Exception as e:
            log_error(f"Error generating trend analysis: {e}")
            return {}
    
    def _generate_tool_analytics(self) -> dict:
        """Generate tool-specific analytics."""
        try:
            analytics = {
                'most_installed': Counter(),
                'most_uninstalled': Counter(),
                'highest_failure_rate': {},
                'installation_duration': defaultdict(list)
            }
            
            for entry in self._history:
                tool_id = entry['tool_id']
                
                if entry['action'] == 'installation':
                    analytics['most_installed'][tool_id] += 1
                    
                    # Track installation duration
                    duration = entry.get('details', {}).get('duration')
                    if duration:
                        analytics['installation_duration'][tool_id].append(duration)
                
                elif entry['action'] == 'uninstallation':
                    analytics['most_uninstalled'][tool_id] += 1
            
            # Calculate failure rates
            tool_stats = defaultdict(lambda: {'total': 0, 'failed': 0})
            
            for entry in self._history:
                if entry['action'] == 'installation':
                    tool_id = entry['tool_id']
                    tool_stats[tool_id]['total'] += 1
                    if not entry['success']:
                        tool_stats[tool_id]['failed'] += 1
            
            for tool_id, stats in tool_stats.items():
                if stats['total'] > 0:
                    failure_rate = stats['failed'] / stats['total']
                    if failure_rate > 0:
                        analytics['highest_failure_rate'][tool_id] = failure_rate
            
            # Convert Counter to dict and calculate averages
            result = {
                'most_installed': dict(analytics['most_installed'].most_common(10)),
                'most_uninstalled': dict(analytics['most_uninstalled'].most_common(10)),
                'highest_failure_rate': dict(sorted(
                    analytics['highest_failure_rate'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]),
                'average_installation_duration': {}
            }
            
            # Calculate average installation durations
            for tool_id, durations in analytics['installation_duration'].items():
                if durations:
                    result['average_installation_duration'][tool_id] = sum(durations) / len(durations)
            
            return result
            
        except Exception as e:
            log_error(f"Error generating tool analytics: {e}")
            return {}
    
    def _generate_time_analytics(self) -> dict:
        """Generate time-based analytics."""
        try:
            analytics = {
                'peak_hours': defaultdict(int),
                'peak_days': defaultdict(int),
                'activity_by_hour': [0] * 24,
                'activity_by_day': defaultdict(int)
            }
            
            for entry in self._history:
                entry_date = self._parse_timestamp(entry['timestamp'])
                
                hour = entry_date.hour
                day_name = entry_date.strftime('%A')
                
                analytics['peak_hours'][hour] += 1
                analytics['peak_days'][day_name] += 1
                analytics['activity_by_hour'][hour] += 1
                analytics['activity_by_day'][day_name] += 1
            
            return {
                'peak_hour': max(analytics['peak_hours'].items(), key=lambda x: x[1])[0] if analytics['peak_hours'] else 0,
                'peak_day': max(analytics['peak_days'].items(), key=lambda x: x[1])[0] if analytics['peak_days'] else 'Unknown',
                'activity_by_hour': analytics['activity_by_hour'],
                'activity_by_day': dict(analytics['activity_by_day'])
            }
            
        except Exception as e:
            log_error(f"Error generating time analytics: {e}")
            return {}
    
    def _generate_performance_metrics(self) -> dict:
        """Generate performance metrics."""
        try:
            durations = []
            sizes = []
            
            for entry in self._history:
                if entry['action'] == 'installation' and entry['success']:
                    details = entry.get('details', {})
                    
                    duration = details.get('duration')
                    if duration:
                        durations.append(duration)
                    
                    size = details.get('size')
                    if size:
                        sizes.append(size)
            
            metrics = {}
            
            if durations:
                metrics['average_install_duration'] = sum(durations) / len(durations)
                metrics['min_install_duration'] = min(durations)
                metrics['max_install_duration'] = max(durations)
            
            if sizes:
                metrics['average_tool_size'] = sum(sizes) / len(sizes)
                metrics['min_tool_size'] = min(sizes)
                metrics['max_tool_size'] = max(sizes)
            
            return metrics
            
        except Exception as e:
            log_error(f"Error generating performance metrics: {e}")
            return {}
    
    def _generate_error_analysis(self) -> dict:
        """Generate error analysis."""
        try:
            error_types = Counter()
            error_tools = Counter()
            
            for entry in self._history:
                if not entry['success'] and entry['action'] == 'installation':
                    tool_id = entry['tool_id']
                    error_msg = entry.get('details', {}).get('error_message', 'Unknown error')
                    
                    error_tools[tool_id] += 1
                    
                    # Categorize errors
                    error_msg_lower = error_msg.lower()
                    if 'network' in error_msg_lower or 'download' in error_msg_lower:
                        error_types['Network/Download'] += 1
                    elif 'permission' in error_msg_lower or 'access' in error_msg_lower:
                        error_types['Permissions'] += 1
                    elif 'dependency' in error_msg_lower or 'missing' in error_msg_lower:
                        error_types['Dependencies'] += 1
                    elif 'disk' in error_msg_lower or 'space' in error_msg_lower:
                        error_types['Disk Space'] += 1
                    else:
                        error_types['Other'] += 1
            
            return {
                'error_types': dict(error_types.most_common()),
                'problematic_tools': dict(error_tools.most_common(10))
            }
            
        except Exception as e:
            log_error(f"Error generating error analysis: {e}")
            return {}