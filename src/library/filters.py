"""
Advanced Filtering System for Sunshine-AIO Community Library

This module provides sophisticated filtering capabilities for community tools
including size, dependency, installation type, and temporal filters.
"""

import os
from typing import List, Dict, Any, Optional, Set, Union
from datetime import datetime, timedelta
import re

from misc.Logger import log_info, log_error, log_warning
from .tool_provider import ToolInfo


class ToolFilter:
    """
    Advanced filtering system for tools with multiple filter criteria
    and intelligent filter combinations.
    """
    
    def __init__(self):
        """Initialize the tool filter system."""
        self._filter_cache: Dict[str, List[ToolInfo]] = {}
        self._available_categories: Set[str] = set()
        self._available_tags: Set[str] = set()
        self._size_units = {
            'b': 1,
            'kb': 1024,
            'mb': 1024 * 1024,
            'gb': 1024 * 1024 * 1024
        }
        
        log_info("ToolFilter initialized")
    
    def apply_filters(self, tools: List[ToolInfo], filters: Dict[str, Any]) -> List[ToolInfo]:
        """
        Apply multiple filters to a list of tools.
        
        Args:
            tools: List of ToolInfo objects to filter
            filters: Dictionary of filter criteria
                    Supported filters:
                    - max_size: Maximum file size in bytes or with unit (e.g., "50MB")
                    - min_size: Minimum file size in bytes or with unit
                    - dependencies: List of required dependencies
                    - installation_types: List of allowed installation types
                    - last_updated_days: Maximum days since last update
                    - platforms: List of target platforms
                    - trust_score_min: Minimum trust score
                    - trust_score_max: Maximum trust score
                    - categories: List of allowed categories
                    - tags: List of required tags (OR logic)
                    - exclude_tags: List of tags to exclude
                    - authors: List of allowed authors
                    - versions: List of version patterns (regex)
                    - has_screenshots: Boolean - require screenshots
                    - verified_only: Boolean - only verified tools
        
        Returns:
            Filtered list of ToolInfo objects
        """
        try:
            if not tools or not filters:
                return tools
            
            # Create cache key from filters
            cache_key = self._create_filter_cache_key(filters)
            tool_ids = [tool.id for tool in tools]
            full_cache_key = f"{cache_key}:{':'.join(sorted(tool_ids))}"
            
            # Check cache
            if full_cache_key in self._filter_cache:
                log_info(f"Returning cached filtered results")
                return self._filter_cache[full_cache_key]
            
            filtered_tools = tools.copy()
            
            # Apply each filter sequentially
            for filter_name, filter_value in filters.items():
                if filter_value is None:
                    continue
                
                if filter_name == 'max_size':
                    filtered_tools = self.filter_by_size(filtered_tools, max_size=filter_value)
                elif filter_name == 'min_size':
                    filtered_tools = self.filter_by_size(filtered_tools, min_size=filter_value)
                elif filter_name == 'dependencies':
                    filtered_tools = self.filter_by_dependencies(filtered_tools, filter_value)
                elif filter_name == 'installation_types':
                    filtered_tools = self.filter_by_installation_type(filtered_tools, filter_value)
                elif filter_name == 'last_updated_days':
                    filtered_tools = self.filter_by_last_updated(filtered_tools, filter_value)
                elif filter_name == 'platforms':
                    filtered_tools = self._filter_by_platforms(filtered_tools, filter_value)
                elif filter_name == 'trust_score_min':
                    filtered_tools = self._filter_by_trust_score(filtered_tools, min_score=filter_value)
                elif filter_name == 'trust_score_max':
                    filtered_tools = self._filter_by_trust_score(filtered_tools, max_score=filter_value)
                elif filter_name == 'categories':
                    filtered_tools = self._filter_by_categories(filtered_tools, filter_value)
                elif filter_name == 'tags':
                    filtered_tools = self._filter_by_tags(filtered_tools, filter_value)
                elif filter_name == 'exclude_tags':
                    filtered_tools = self._filter_exclude_tags(filtered_tools, filter_value)
                elif filter_name == 'authors':
                    filtered_tools = self._filter_by_authors(filtered_tools, filter_value)
                elif filter_name == 'versions':
                    filtered_tools = self._filter_by_versions(filtered_tools, filter_value)
                elif filter_name == 'has_screenshots':
                    filtered_tools = self._filter_by_screenshots(filtered_tools, filter_value)
                elif filter_name == 'verified_only':
                    filtered_tools = self._filter_by_verification(filtered_tools, filter_value)
                else:
                    log_warning(f"Unknown filter: {filter_name}")
            
            # Cache the results
            self._filter_cache[full_cache_key] = filtered_tools
            
            log_info(f"Applied filters reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error applying filters: {e}")
            return tools
    
    def filter_by_size(self, tools: List[ToolInfo], max_size: Union[int, str] = None, 
                      min_size: Union[int, str] = None) -> List[ToolInfo]:
        """
        Filter tools by file size.
        
        Args:
            tools: List of ToolInfo objects to filter
            max_size: Maximum size in bytes or with unit (e.g., "50MB")
            min_size: Minimum size in bytes or with unit
            
        Returns:
            Filtered list of ToolInfo objects
        """
        try:
            if not tools:
                return tools
            
            # Convert size strings to bytes
            max_bytes = self._parse_size(max_size) if max_size else None
            min_bytes = self._parse_size(min_size) if min_size else None
            
            filtered_tools = []
            
            for tool in tools:
                tool_size = getattr(tool, 'size', 0)
                if isinstance(tool_size, str):
                    tool_size = self._parse_size(tool_size)
                
                # Apply size filters
                if max_bytes is not None and tool_size > max_bytes:
                    continue
                if min_bytes is not None and tool_size < min_bytes:
                    continue
                
                filtered_tools.append(tool)
            
            log_info(f"Size filter reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by size: {e}")
            return tools
    
    def filter_by_dependencies(self, tools: List[ToolInfo], available_deps: List[str]) -> List[ToolInfo]:
        """
        Filter tools by available dependencies.
        
        Args:
            tools: List of ToolInfo objects to filter
            available_deps: List of available dependency names
            
        Returns:
            Filtered list of ToolInfo objects with satisfied dependencies
        """
        try:
            if not tools or not available_deps:
                return tools
            
            available_deps_lower = [dep.lower() for dep in available_deps]
            filtered_tools = []
            
            for tool in tools:
                tool_deps = getattr(tool, 'dependencies', [])
                if isinstance(tool_deps, str):
                    tool_deps = [tool_deps]
                
                # Check if all tool dependencies are available
                missing_deps = []
                for dep in tool_deps:
                    if dep.lower() not in available_deps_lower:
                        missing_deps.append(dep)
                
                # Include tool only if all dependencies are met
                if not missing_deps:
                    filtered_tools.append(tool)
            
            log_info(f"Dependency filter reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by dependencies: {e}")
            return tools
    
    def filter_by_installation_type(self, tools: List[ToolInfo], install_types: List[str]) -> List[ToolInfo]:
        """
        Filter tools by installation type.
        
        Args:
            tools: List of ToolInfo objects to filter
            install_types: List of allowed installation types
                          (e.g., ['portable', 'installer', 'script', 'python'])
            
        Returns:
            Filtered list of ToolInfo objects
        """
        try:
            if not tools or not install_types:
                return tools
            
            install_types_lower = [t.lower() for t in install_types]
            filtered_tools = []
            
            for tool in tools:
                tool_type = getattr(tool, 'installation_type', 'unknown').lower()
                
                # Check if tool installation type is allowed
                if tool_type in install_types_lower:
                    filtered_tools.append(tool)
                else:
                    # Check for partial matches
                    for allowed_type in install_types_lower:
                        if allowed_type in tool_type or tool_type in allowed_type:
                            filtered_tools.append(tool)
                            break
            
            log_info(f"Installation type filter reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by installation type: {e}")
            return tools
    
    def filter_by_last_updated(self, tools: List[ToolInfo], days: int) -> List[ToolInfo]:
        """
        Filter tools by last update time.
        
        Args:
            tools: List of ToolInfo objects to filter
            days: Maximum days since last update
            
        Returns:
            Filtered list of recently updated tools
        """
        try:
            if not tools or days < 0:
                return tools
            
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered_tools = []
            
            for tool in tools:
                last_updated = getattr(tool, 'last_updated', None)
                
                if not last_updated:
                    # If no update date, check date_added
                    last_updated = getattr(tool, 'date_added', None)
                
                if last_updated:
                    try:
                        # Parse date string
                        if isinstance(last_updated, str):
                            # Try different date formats
                            date_formats = [
                                '%Y-%m-%d',
                                '%Y-%m-%dT%H:%M:%S',
                                '%Y-%m-%d %H:%M:%S',
                                '%Y-%m-%dT%H:%M:%S.%f'
                            ]
                            
                            update_date = None
                            for fmt in date_formats:
                                try:
                                    update_date = datetime.strptime(last_updated.split('.')[0], fmt)
                                    break
                                except ValueError:
                                    continue
                            
                            if update_date and update_date >= cutoff_date:
                                filtered_tools.append(tool)
                        elif isinstance(last_updated, datetime):
                            if last_updated >= cutoff_date:
                                filtered_tools.append(tool)
                        
                    except Exception as e:
                        log_warning(f"Error parsing date for tool {tool.id}: {e}")
                        # Include tool if date parsing fails
                        filtered_tools.append(tool)
                else:
                    # Include tools without date information
                    filtered_tools.append(tool)
            
            log_info(f"Last updated filter reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by last updated: {e}")
            return tools
    
    def get_available_categories(self, tools: List[ToolInfo]) -> List[str]:
        """
        Get all available categories from a list of tools.
        
        Args:
            tools: List of ToolInfo objects
            
        Returns:
            Sorted list of unique categories
        """
        try:
            categories = set()
            
            for tool in tools:
                category = getattr(tool, 'category', None)
                if category:
                    categories.add(category)
            
            self._available_categories = categories
            return sorted(list(categories))
            
        except Exception as e:
            log_error(f"Error getting categories: {e}")
            return []
    
    def get_available_tags(self, tools: List[ToolInfo]) -> List[str]:
        """
        Get all available tags from a list of tools.
        
        Args:
            tools: List of ToolInfo objects
            
        Returns:
            Sorted list of unique tags
        """
        try:
            tags = set()
            
            for tool in tools:
                tool_tags = getattr(tool, 'tags', [])
                if isinstance(tool_tags, str):
                    tool_tags = [tool_tags]
                
                for tag in tool_tags:
                    if tag:
                        tags.add(tag)
            
            self._available_tags = tags
            return sorted(list(tags))
            
        except Exception as e:
            log_error(f"Error getting tags: {e}")
            return []
    
    def get_filter_statistics(self, tools: List[ToolInfo]) -> Dict[str, Any]:
        """
        Get statistics about filterable attributes.
        
        Args:
            tools: List of ToolInfo objects
            
        Returns:
            Dictionary with filter statistics
        """
        try:
            stats = {
                'total_tools': len(tools),
                'categories': {},
                'tags': {},
                'platforms': {},
                'installation_types': {},
                'authors': {},
                'size_distribution': {'small': 0, 'medium': 0, 'large': 0},
                'trust_score_distribution': {
                    'high': 0, 'medium': 0, 'low': 0, 'unrated': 0
                },
                'verification_status': {'verified': 0, 'unverified': 0}
            }
            
            for tool in tools:
                # Categories
                category = getattr(tool, 'category', 'Unknown')
                stats['categories'][category] = stats['categories'].get(category, 0) + 1
                
                # Tags
                tool_tags = getattr(tool, 'tags', [])
                if isinstance(tool_tags, str):
                    tool_tags = [tool_tags]
                for tag in tool_tags:
                    if tag:
                        stats['tags'][tag] = stats['tags'].get(tag, 0) + 1
                
                # Platforms
                platforms = getattr(tool, 'platforms', ['unknown'])
                if isinstance(platforms, str):
                    platforms = [platforms]
                for platform in platforms:
                    stats['platforms'][platform] = stats['platforms'].get(platform, 0) + 1
                
                # Installation types
                install_type = getattr(tool, 'installation_type', 'unknown')
                stats['installation_types'][install_type] = stats['installation_types'].get(install_type, 0) + 1
                
                # Authors
                author = getattr(tool, 'author', 'Unknown')
                stats['authors'][author] = stats['authors'].get(author, 0) + 1
                
                # Size distribution
                size = getattr(tool, 'size', 0)
                if isinstance(size, str):
                    size = self._parse_size(size)
                
                if size < 1024 * 1024:  # < 1MB
                    stats['size_distribution']['small'] += 1
                elif size < 100 * 1024 * 1024:  # < 100MB
                    stats['size_distribution']['medium'] += 1
                else:
                    stats['size_distribution']['large'] += 1
                
                # Trust score distribution
                trust_score = getattr(tool, 'trust_score', None)
                if trust_score is None:
                    stats['trust_score_distribution']['unrated'] += 1
                elif trust_score >= 8.0:
                    stats['trust_score_distribution']['high'] += 1
                elif trust_score >= 5.0:
                    stats['trust_score_distribution']['medium'] += 1
                else:
                    stats['trust_score_distribution']['low'] += 1
                
                # Verification status
                verified = getattr(tool, 'verified', False)
                if verified:
                    stats['verification_status']['verified'] += 1
                else:
                    stats['verification_status']['unverified'] += 1
            
            return stats
            
        except Exception as e:
            log_error(f"Error generating filter statistics: {e}")
            return {'total_tools': len(tools), 'error': str(e)}
    
    def clear_cache(self) -> None:
        """Clear the filter cache."""
        self._filter_cache.clear()
        log_info("Filter cache cleared")
    
    def _filter_by_platforms(self, tools: List[ToolInfo], platforms: List[str]) -> List[ToolInfo]:
        """Filter tools by supported platforms."""
        platforms_lower = [p.lower() for p in platforms]
        filtered_tools = []
        
        for tool in tools:
            tool_platforms = getattr(tool, 'platforms', ['windows'])
            if isinstance(tool_platforms, str):
                tool_platforms = [tool_platforms]
            
            tool_platforms_lower = [p.lower() for p in tool_platforms]
            
            # Check if any platform matches
            if any(platform in tool_platforms_lower for platform in platforms_lower):
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_trust_score(self, tools: List[ToolInfo], min_score: float = None, 
                              max_score: float = None) -> List[ToolInfo]:
        """Filter tools by trust score range."""
        filtered_tools = []
        
        for tool in tools:
            trust_score = getattr(tool, 'trust_score', 5.0)
            
            if min_score is not None and trust_score < min_score:
                continue
            if max_score is not None and trust_score > max_score:
                continue
            
            filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_categories(self, tools: List[ToolInfo], categories: List[str]) -> List[ToolInfo]:
        """Filter tools by categories."""
        categories_lower = [c.lower() for c in categories]
        filtered_tools = []
        
        for tool in tools:
            tool_category = getattr(tool, 'category', '').lower()
            if tool_category in categories_lower:
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_tags(self, tools: List[ToolInfo], tags: List[str]) -> List[ToolInfo]:
        """Filter tools by tags (OR logic)."""
        tags_lower = [t.lower() for t in tags]
        filtered_tools = []
        
        for tool in tools:
            tool_tags = getattr(tool, 'tags', [])
            if isinstance(tool_tags, str):
                tool_tags = [tool_tags]
            
            tool_tags_lower = [t.lower() for t in tool_tags if t]
            
            # Check if any tag matches
            if any(tag in tool_tags_lower for tag in tags_lower):
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_exclude_tags(self, tools: List[ToolInfo], exclude_tags: List[str]) -> List[ToolInfo]:
        """Filter out tools with specified tags."""
        exclude_tags_lower = [t.lower() for t in exclude_tags]
        filtered_tools = []
        
        for tool in tools:
            tool_tags = getattr(tool, 'tags', [])
            if isinstance(tool_tags, str):
                tool_tags = [tool_tags]
            
            tool_tags_lower = [t.lower() for t in tool_tags if t]
            
            # Exclude if any tag matches
            if not any(tag in tool_tags_lower for tag in exclude_tags_lower):
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_authors(self, tools: List[ToolInfo], authors: List[str]) -> List[ToolInfo]:
        """Filter tools by authors."""
        authors_lower = [a.lower() for a in authors]
        filtered_tools = []
        
        for tool in tools:
            tool_author = getattr(tool, 'author', '').lower()
            if tool_author in authors_lower:
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_versions(self, tools: List[ToolInfo], version_patterns: List[str]) -> List[ToolInfo]:
        """Filter tools by version patterns (regex)."""
        filtered_tools = []
        
        for tool in tools:
            tool_version = getattr(tool, 'version', '')
            
            # Check if version matches any pattern
            for pattern in version_patterns:
                try:
                    if re.match(pattern, tool_version):
                        filtered_tools.append(tool)
                        break
                except re.error:
                    # If regex is invalid, try literal match
                    if pattern in tool_version:
                        filtered_tools.append(tool)
                        break
        
        return filtered_tools
    
    def _filter_by_screenshots(self, tools: List[ToolInfo], has_screenshots: bool) -> List[ToolInfo]:
        """Filter tools by screenshot availability."""
        filtered_tools = []
        
        for tool in tools:
            screenshots = getattr(tool, 'screenshots', [])
            has_screens = screenshots and len(screenshots) > 0
            
            if has_screenshots == has_screens:
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _filter_by_verification(self, tools: List[ToolInfo], verified_only: bool) -> List[ToolInfo]:
        """Filter tools by verification status."""
        if not verified_only:
            return tools
        
        filtered_tools = []
        
        for tool in tools:
            verified = getattr(tool, 'verified', False)
            if verified:
                filtered_tools.append(tool)
        
        return filtered_tools
    
    def _parse_size(self, size: Union[int, str]) -> int:
        """
        Parse size string to bytes.
        
        Args:
            size: Size as integer (bytes) or string with unit (e.g., "50MB")
            
        Returns:
            Size in bytes
        """
        try:
            if isinstance(size, int):
                return size
            
            if isinstance(size, str):
                size = size.strip().lower()
                
                # Extract number and unit
                match = re.match(r'(\d+(?:\.\d+)?)\s*([a-z]*)', size)
                if match:
                    number, unit = match.groups()
                    number = float(number)
                    
                    # Convert to bytes
                    unit = unit or 'b'
                    multiplier = self._size_units.get(unit, 1)
                    return int(number * multiplier)
            
            return 0
            
        except Exception as e:
            log_error(f"Error parsing size '{size}': {e}")
            return 0
    
    def _create_filter_cache_key(self, filters: Dict[str, Any]) -> str:
        """Create a cache key from filter dictionary."""
        try:
            # Sort filters for consistent cache keys
            sorted_filters = sorted(filters.items())
            
            # Convert to string representation
            filter_parts = []
            for key, value in sorted_filters:
                if isinstance(value, list):
                    value_str = ':'.join(sorted(str(v) for v in value))
                else:
                    value_str = str(value)
                filter_parts.append(f"{key}={value_str}")
            
            return '|'.join(filter_parts)
            
        except Exception as e:
            log_error(f"Error creating cache key: {e}")
            return "invalid_cache_key"