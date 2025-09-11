"""
Advanced Search Engine for Sunshine-AIO Community Library

This module provides comprehensive search capabilities for community tools including
fuzzy search, category filtering, tag-based search, and intelligent suggestions.
"""

import os
import re
from typing import List, Dict, Any, Optional, Union, Set
from difflib import SequenceMatcher
from collections import defaultdict, Counter
import json

from misc.Logger import log_info, log_error, log_warning
from .tool_provider import ToolInfo


class ToolSearchEngine:
    """
    Advanced search engine for community tools with fuzzy matching,
    intelligent filtering, and search suggestions.
    """
    
    def __init__(self, library_manager):
        """
        Initialize the search engine.
        
        Args:
            library_manager: LibraryManager instance for accessing tool data
        """
        self.library_manager = library_manager
        self._search_cache: Dict[str, List[ToolInfo]] = {}
        self._suggestion_cache: Dict[str, List[str]] = {}
        self._stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
        
        log_info("ToolSearchEngine initialized")
    
    def search_by_name(self, query: str, fuzzy: bool = True) -> List[ToolInfo]:
        """
        Search tools by name with optional fuzzy matching.
        
        Args:
            query: Search query string
            fuzzy: Enable fuzzy matching for approximate results
            
        Returns:
            List of matching ToolInfo objects sorted by relevance
        """
        try:
            if not query or not query.strip():
                return []
            
            query = query.strip().lower()
            cache_key = f"name:{query}:fuzzy:{fuzzy}"
            
            # Check cache first
            if cache_key in self._search_cache:
                log_info(f"Returning cached results for name search: {query}")
                return self._search_cache[cache_key]
            
            tools_dict = self.library_manager.get_available_tools()
            results = []
            
            for tool_id, tool_data in tools_dict.items():
                tool_info = self._dict_to_tool_info(tool_data, tool_id)
                score = self._calculate_name_score(query, tool_info, fuzzy)
                
                if score > 0:
                    results.append((tool_info, score))
            
            # Sort by score (highest first)
            results.sort(key=lambda x: x[1], reverse=True)
            final_results = [tool for tool, _ in results]
            
            # Cache results
            self._search_cache[cache_key] = final_results
            
            log_info(f"Name search for '{query}' returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            log_error(f"Error in name search: {e}")
            return []
    
    def search_by_category(self, category: str) -> List[ToolInfo]:
        """
        Search tools by category.
        
        Args:
            category: Category name to search for
            
        Returns:
            List of ToolInfo objects in the specified category
        """
        try:
            if not category or not category.strip():
                return []
            
            category = category.strip().lower()
            cache_key = f"category:{category}"
            
            # Check cache first
            if cache_key in self._search_cache:
                log_info(f"Returning cached results for category: {category}")
                return self._search_cache[cache_key]
            
            tools_dict = self.library_manager.get_available_tools()
            results = []
            
            for tool_id, tool_data in tools_dict.items():
                tool_category = tool_data.get('category', '').lower()
                if category in tool_category or tool_category in category:
                    tool_info = self._dict_to_tool_info(tool_data, tool_id)
                    results.append(tool_info)
            
            # Sort by name
            results.sort(key=lambda x: x.name.lower())
            
            # Cache results
            self._search_cache[cache_key] = results
            
            log_info(f"Category search for '{category}' returned {len(results)} results")
            return results
            
        except Exception as e:
            log_error(f"Error in category search: {e}")
            return []
    
    def search_by_tags(self, tags: List[str]) -> List[ToolInfo]:
        """
        Search tools by tags with AND/OR logic.
        
        Args:
            tags: List of tag strings to search for
            
        Returns:
            List of ToolInfo objects matching the tags
        """
        try:
            if not tags:
                return []
            
            # Normalize tags
            normalized_tags = [tag.strip().lower() for tag in tags if tag.strip()]
            if not normalized_tags:
                return []
            
            cache_key = f"tags:{':'.join(sorted(normalized_tags))}"
            
            # Check cache first
            if cache_key in self._search_cache:
                log_info(f"Returning cached results for tags: {tags}")
                return self._search_cache[cache_key]
            
            tools_dict = self.library_manager.get_available_tools()
            results = []
            
            for tool_id, tool_data in tools_dict.items():
                tool_tags = tool_data.get('tags', [])
                if isinstance(tool_tags, str):
                    tool_tags = [tool_tags]
                
                # Convert to lowercase for comparison
                tool_tags_lower = [tag.lower() for tag in tool_tags if tag]
                
                # Check if any of the search tags match
                if any(search_tag in tool_tags_lower for search_tag in normalized_tags):
                    tool_info = self._dict_to_tool_info(tool_data, tool_id)
                    
                    # Calculate match score based on number of matching tags
                    match_count = sum(1 for tag in normalized_tags if tag in tool_tags_lower)
                    results.append((tool_info, match_count))
            
            # Sort by match score (highest first)
            results.sort(key=lambda x: x[1], reverse=True)
            final_results = [tool for tool, _ in results]
            
            # Cache results
            self._search_cache[cache_key] = final_results
            
            log_info(f"Tag search for {tags} returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            log_error(f"Error in tag search: {e}")
            return []
    
    def search_by_description(self, query: str) -> List[ToolInfo]:
        """
        Search tools by description content with keyword matching.
        
        Args:
            query: Search query string
            
        Returns:
            List of ToolInfo objects with matching descriptions
        """
        try:
            if not query or not query.strip():
                return []
            
            query = query.strip().lower()
            cache_key = f"description:{query}"
            
            # Check cache first
            if cache_key in self._search_cache:
                log_info(f"Returning cached results for description search: {query}")
                return self._search_cache[cache_key]
            
            # Extract keywords from query (remove stop words)
            keywords = self._extract_keywords(query)
            if not keywords:
                return []
            
            tools_dict = self.library_manager.get_available_tools()
            results = []
            
            for tool_id, tool_data in tools_dict.items():
                description = tool_data.get('description', '').lower()
                score = self._calculate_description_score(keywords, description)
                
                if score > 0:
                    tool_info = self._dict_to_tool_info(tool_data, tool_id)
                    results.append((tool_info, score))
            
            # Sort by score (highest first)
            results.sort(key=lambda x: x[1], reverse=True)
            final_results = [tool for tool, _ in results]
            
            # Cache results
            self._search_cache[cache_key] = final_results
            
            log_info(f"Description search for '{query}' returned {len(final_results)} results")
            return final_results
            
        except Exception as e:
            log_error(f"Error in description search: {e}")
            return []
    
    def filter_by_platform(self, tools: List[ToolInfo], platform: str) -> List[ToolInfo]:
        """
        Filter tools by target platform.
        
        Args:
            tools: List of ToolInfo objects to filter
            platform: Target platform (windows, linux, mac, cross-platform)
            
        Returns:
            Filtered list of ToolInfo objects
        """
        try:
            if not tools or not platform:
                return tools
            
            platform = platform.strip().lower()
            filtered_tools = []
            
            for tool in tools:
                tool_platforms = getattr(tool, 'platforms', ['windows'])
                if isinstance(tool_platforms, str):
                    tool_platforms = [tool_platforms]
                
                # Convert to lowercase for comparison
                tool_platforms_lower = [p.lower() for p in tool_platforms]
                
                # Check for platform match
                if (platform in tool_platforms_lower or 
                    'cross-platform' in tool_platforms_lower or
                    'all' in tool_platforms_lower):
                    filtered_tools.append(tool)
            
            log_info(f"Platform filter '{platform}' reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by platform: {e}")
            return tools
    
    def filter_by_trust_level(self, tools: List[ToolInfo], min_trust: float) -> List[ToolInfo]:
        """
        Filter tools by minimum trust level.
        
        Args:
            tools: List of ToolInfo objects to filter
            min_trust: Minimum trust score (0.0 to 10.0)
            
        Returns:
            Filtered list of ToolInfo objects
        """
        try:
            if not tools or min_trust < 0:
                return tools
            
            filtered_tools = []
            
            for tool in tools:
                trust_score = getattr(tool, 'trust_score', 5.0)
                if trust_score >= min_trust:
                    filtered_tools.append(tool)
            
            log_info(f"Trust filter {min_trust}+ reduced {len(tools)} to {len(filtered_tools)} tools")
            return filtered_tools
            
        except Exception as e:
            log_error(f"Error filtering by trust level: {e}")
            return tools
    
    def sort_tools(self, tools: List[ToolInfo], sort_by: str, reverse: bool = False) -> List[ToolInfo]:
        """
        Sort tools by specified criteria.
        
        Args:
            tools: List of ToolInfo objects to sort
            sort_by: Sort criteria (name, category, trust_score, size, date_added)
            reverse: Sort in descending order if True
            
        Returns:
            Sorted list of ToolInfo objects
        """
        try:
            if not tools or not sort_by:
                return tools
            
            sort_by = sort_by.lower()
            
            if sort_by == 'name':
                return sorted(tools, key=lambda x: x.name.lower(), reverse=reverse)
            elif sort_by == 'category':
                return sorted(tools, key=lambda x: getattr(x, 'category', '').lower(), reverse=reverse)
            elif sort_by == 'trust_score':
                return sorted(tools, key=lambda x: getattr(x, 'trust_score', 5.0), reverse=reverse)
            elif sort_by == 'size':
                return sorted(tools, key=lambda x: getattr(x, 'size', 0), reverse=reverse)
            elif sort_by == 'date_added':
                return sorted(tools, key=lambda x: getattr(x, 'date_added', ''), reverse=reverse)
            else:
                log_warning(f"Unknown sort criteria: {sort_by}")
                return tools
            
        except Exception as e:
            log_error(f"Error sorting tools: {e}")
            return tools
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            
        Returns:
            List of suggested search terms
        """
        try:
            if not partial_query or len(partial_query) < 2:
                return []
            
            partial_query = partial_query.strip().lower()
            
            # Check cache first
            if partial_query in self._suggestion_cache:
                return self._suggestion_cache[partial_query]
            
            tools_dict = self.library_manager.get_available_tools()
            suggestions = set()
            
            # Collect potential suggestions from tool names, categories, and tags
            for tool_id, tool_data in tools_dict.items():
                # Tool names
                tool_name = tool_data.get('name', '').lower()
                if partial_query in tool_name:
                    suggestions.add(tool_data.get('name', ''))
                
                # Tool IDs
                if partial_query in tool_id.lower():
                    suggestions.add(tool_id.replace('_', ' ').replace('-', ' ').title())
                
                # Categories
                category = tool_data.get('category', '').lower()
                if partial_query in category:
                    suggestions.add(tool_data.get('category', ''))
                
                # Tags
                tags = tool_data.get('tags', [])
                if isinstance(tags, str):
                    tags = [tags]
                
                for tag in tags:
                    if tag and partial_query in tag.lower():
                        suggestions.add(tag)
                
                # Description keywords
                description = tool_data.get('description', '').lower()
                words = re.findall(r'\b\w{3,}\b', description)
                for word in words:
                    if partial_query in word and word not in self._stop_words:
                        suggestions.add(word.title())
            
            # Convert to sorted list and limit results
            suggestion_list = sorted(list(suggestions))[:10]
            
            # Cache suggestions
            self._suggestion_cache[partial_query] = suggestion_list
            
            log_info(f"Generated {len(suggestion_list)} suggestions for '{partial_query}'")
            return suggestion_list
            
        except Exception as e:
            log_error(f"Error generating suggestions: {e}")
            return []
    
    def combined_search(self, query: str, categories: List[str] = None, 
                       tags: List[str] = None, platform: str = None,
                       min_trust: float = 0.0, fuzzy: bool = True) -> List[ToolInfo]:
        """
        Perform a combined search using multiple criteria.
        
        Args:
            query: Text query for name and description search
            categories: List of categories to filter by
            tags: List of tags to filter by
            platform: Platform to filter by
            min_trust: Minimum trust score
            fuzzy: Enable fuzzy matching
            
        Returns:
            List of ToolInfo objects matching all criteria
        """
        try:
            log_info(f"Performing combined search: query='{query}', categories={categories}, tags={tags}")
            
            # Start with all tools if no query provided
            if query and query.strip():
                # Combine name and description search results
                name_results = self.search_by_name(query, fuzzy)
                desc_results = self.search_by_description(query)
                
                # Merge and deduplicate results
                all_results = {}
                for tool in name_results:
                    all_results[tool.id] = tool
                for tool in desc_results:
                    all_results[tool.id] = tool
                
                results = list(all_results.values())
            else:
                # Start with all available tools
                tools_dict = self.library_manager.get_available_tools()
                results = [self._dict_to_tool_info(data, tool_id) for tool_id, data in tools_dict.items()]
            
            # Apply category filter
            if categories:
                category_results = []
                for category in categories:
                    category_tools = self.search_by_category(category)
                    category_results.extend(category_tools)
                
                # Intersect with current results
                if results:
                    result_ids = {tool.id for tool in results}
                    category_ids = {tool.id for tool in category_results}
                    intersect_ids = result_ids.intersection(category_ids)
                    results = [tool for tool in results if tool.id in intersect_ids]
                else:
                    results = category_results
            
            # Apply tag filter
            if tags:
                tag_results = self.search_by_tags(tags)
                if results:
                    result_ids = {tool.id for tool in results}
                    tag_ids = {tool.id for tool in tag_results}
                    intersect_ids = result_ids.intersection(tag_ids)
                    results = [tool for tool in results if tool.id in intersect_ids]
                else:
                    results = tag_results
            
            # Apply platform filter
            if platform:
                results = self.filter_by_platform(results, platform)
            
            # Apply trust level filter
            if min_trust > 0:
                results = self.filter_by_trust_level(results, min_trust)
            
            log_info(f"Combined search returned {len(results)} results")
            return results
            
        except Exception as e:
            log_error(f"Error in combined search: {e}")
            return []
    
    def clear_cache(self) -> None:
        """Clear all search caches."""
        self._search_cache.clear()
        self._suggestion_cache.clear()
        log_info("Search cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get search cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'search_cache_size': len(self._search_cache),
            'suggestion_cache_size': len(self._suggestion_cache)
        }
    
    def _dict_to_tool_info(self, tool_data: Dict[str, Any], tool_id: str) -> ToolInfo:
        """
        Convert tool dictionary to ToolInfo object.
        
        Args:
            tool_data: Tool data dictionary
            tool_id: Tool ID
            
        Returns:
            ToolInfo object
        """
        try:
            # Use ToolInfo.from_dict if available, otherwise create manually
            if hasattr(ToolInfo, 'from_dict'):
                return ToolInfo.from_dict(tool_data)
            else:
                # Manual creation as fallback
                return ToolInfo(
                    id=tool_id,
                    name=tool_data.get('name', tool_id),
                    description=tool_data.get('description', ''),
                    category=tool_data.get('category', 'General'),
                    version=tool_data.get('version', '1.0.0'),
                    author=tool_data.get('author', 'Unknown'),
                    download_url=tool_data.get('download_url', ''),
                    size=tool_data.get('size', 0),
                    trust_score=tool_data.get('trust_score', 5.0),
                    platforms=tool_data.get('platforms', ['windows']),
                    tags=tool_data.get('tags', [])
                )
        except Exception as e:
            log_error(f"Error creating ToolInfo for {tool_id}: {e}")
            # Return minimal ToolInfo as fallback
            return ToolInfo(
                id=tool_id,
                name=tool_data.get('name', tool_id),
                description=tool_data.get('description', ''),
                category='General',
                version='1.0.0',
                author='Unknown'
            )
    
    def _calculate_name_score(self, query: str, tool_info: ToolInfo, fuzzy: bool) -> float:
        """
        Calculate relevance score for name matching.
        
        Args:
            query: Search query
            tool_info: ToolInfo object
            fuzzy: Enable fuzzy matching
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        try:
            name = tool_info.name.lower()
            tool_id = tool_info.id.lower()
            
            # Exact match gets highest score
            if query == name or query == tool_id:
                return 1.0
            
            # Starts with query gets high score
            if name.startswith(query) or tool_id.startswith(query):
                return 0.9
            
            # Contains query gets medium score
            if query in name or query in tool_id:
                return 0.7
            
            # Fuzzy matching
            if fuzzy:
                name_ratio = SequenceMatcher(None, query, name).ratio()
                id_ratio = SequenceMatcher(None, query, tool_id).ratio()
                max_ratio = max(name_ratio, id_ratio)
                
                # Only return if similarity is above threshold
                if max_ratio >= 0.6:
                    return max_ratio * 0.6  # Scale down fuzzy matches
            
            return 0.0
            
        except Exception as e:
            log_error(f"Error calculating name score: {e}")
            return 0.0
    
    def _calculate_description_score(self, keywords: List[str], description: str) -> float:
        """
        Calculate relevance score for description matching.
        
        Args:
            keywords: List of search keywords
            description: Tool description
            
        Returns:
            Relevance score based on keyword matches
        """
        try:
            if not keywords or not description:
                return 0.0
            
            total_score = 0.0
            matched_keywords = 0
            
            for keyword in keywords:
                if keyword in description:
                    matched_keywords += 1
                    # Exact word boundary match gets higher score
                    if re.search(r'\b' + re.escape(keyword) + r'\b', description):
                        total_score += 1.0
                    else:
                        total_score += 0.5
            
            # Normalize score by number of keywords
            if len(keywords) > 0:
                return min(total_score / len(keywords), 1.0)
            
            return 0.0
            
        except Exception as e:
            log_error(f"Error calculating description score: {e}")
            return 0.0
    
    def _extract_keywords(self, query: str) -> List[str]:
        """
        Extract meaningful keywords from search query.
        
        Args:
            query: Search query string
            
        Returns:
            List of keywords
        """
        try:
            # Remove punctuation and split into words
            words = re.findall(r'\b\w{2,}\b', query.lower())
            
            # Filter out stop words and short words
            keywords = [word for word in words if word not in self._stop_words and len(word) >= 3]
            
            return keywords
            
        except Exception as e:
            log_error(f"Error extracting keywords: {e}")
            return []