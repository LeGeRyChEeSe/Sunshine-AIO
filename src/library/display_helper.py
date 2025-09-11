"""
Rich Display Helper for Sunshine-AIO Community Library

This module provides sophisticated display formatting for tool information,
search results, comparisons, and installation status with professional styling.
"""

import os
import math
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from misc.Logger import log_info, log_error, log_warning
from .tool_provider import ToolInfo


class ToolDisplayHelper:
    """
    Helper for rich tool information display with professional formatting,
    pagination, and advanced visualization capabilities.
    """
    
    def __init__(self):
        """Initialize the display helper."""
        self.console_width = 120  # Default console width
        self.max_description_length = 100
        self.colors_enabled = True
        
        # Display symbols and formatting
        self.symbols = {
            'star': '★',
            'heart': '♥',
            'check': '✓',
            'cross': '✗',
            'warning': '⚠',
            'info': 'ℹ',
            'download': '↓',
            'size': '📁',
            'author': '👤',
            'category': '📂',
            'platform': '🖥',
            'trust': '🛡',
            'verified': '✓',
            'new': '🆕',
            'updated': '🔄'
        }
        
        # Color codes (if terminal supports colors)
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'dim': '\033[2m',
            'underline': '\033[4m',
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'gray': '\033[90m'
        }
        
        log_info("ToolDisplayHelper initialized")
    
    def format_tool_info(self, tool: ToolInfo, detailed: bool = False) -> str:
        """
        Format detailed tool information.
        
        Args:
            tool: ToolInfo object to format
            detailed: Show detailed information including dependencies
            
        Returns:
            Formatted tool information string
        """
        try:
            lines = []
            
            # Header with tool name and basic info
            header = self._format_tool_header(tool)
            lines.append(header)
            lines.append(self._create_separator())
            
            # Basic information
            lines.extend(self._format_basic_info(tool))
            
            if detailed:
                # Detailed information
                lines.append("")
                lines.extend(self._format_detailed_info(tool))
            
            # Footer with actions
            lines.append("")
            lines.append(self._format_tool_actions(tool))
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting tool info: {e}")
            return f"Error displaying tool information for {getattr(tool, 'id', 'unknown')}"
    
    def format_tool_list(self, tools: List[ToolInfo], page: int = 1, per_page: int = 10) -> str:
        """
        Format a list of tools with pagination.
        
        Args:
            tools: List of ToolInfo objects
            page: Current page number (1-based)
            per_page: Number of tools per page
            
        Returns:
            Formatted tool list string
        """
        try:
            if not tools:
                return self._colorize("No tools found.", 'yellow')
            
            # Calculate pagination
            total_tools = len(tools)
            total_pages = math.ceil(total_tools / per_page)
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total_tools)
            page_tools = tools[start_idx:end_idx]
            
            lines = []
            
            # Header
            header = f"Community Tools ({total_tools} total)"
            lines.append(self._colorize(header, 'bold'))
            lines.append(self._create_separator())
            
            # Tool list
            for i, tool in enumerate(page_tools, start=start_idx + 1):
                tool_line = self._format_tool_list_item(tool, i)
                lines.append(tool_line)
            
            # Pagination info
            if total_pages > 1:
                lines.append("")
                pagination = f"Page {page} of {total_pages} | Showing {start_idx + 1}-{end_idx} of {total_tools}"
                lines.append(self._colorize(pagination, 'dim'))
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting tool list: {e}")
            return "Error displaying tool list"
    
    def format_search_results(self, tools: List[ToolInfo], query: str) -> str:
        """
        Format search results with highlighted query terms.
        
        Args:
            tools: List of matching ToolInfo objects
            query: Search query used
            
        Returns:
            Formatted search results string
        """
        try:
            lines = []
            
            # Header
            query_display = self._colorize(f"'{query}'", 'yellow')
            header = f"Search Results for {query_display} ({len(tools)} found)"
            lines.append(self._colorize(header, 'bold'))
            lines.append(self._create_separator())
            
            if not tools:
                lines.append(self._colorize("No tools found matching your search.", 'yellow'))
                lines.append("")
                lines.append("Try:")
                lines.append("• Using different keywords")
                lines.append("• Checking spelling")
                lines.append("• Using broader search terms")
                lines.append("• Browsing categories instead")
                return "\n".join(lines)
            
            # Search results
            for i, tool in enumerate(tools, 1):
                result_line = self._format_search_result_item(tool, i, query)
                lines.append(result_line)
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting search results: {e}")
            return f"Error displaying search results for '{query}'"
    
    def format_comparison_table(self, tools: List[ToolInfo]) -> str:
        """
        Format tools in a comparison table.
        
        Args:
            tools: List of ToolInfo objects to compare
            
        Returns:
            Formatted comparison table string
        """
        try:
            if not tools:
                return self._colorize("No tools to compare.", 'yellow')
            
            if len(tools) > 4:
                tools = tools[:4]  # Limit to 4 tools for readability
            
            lines = []
            
            # Header
            header = f"Tool Comparison ({len(tools)} tools)"
            lines.append(self._colorize(header, 'bold'))
            lines.append(self._create_separator())
            
            # Prepare comparison data
            comparison_data = self._prepare_comparison_data(tools)
            
            # Format table
            table_lines = self._format_comparison_table_rows(comparison_data)
            lines.extend(table_lines)
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting comparison table: {e}")
            return "Error displaying comparison table"
    
    def format_installation_status(self, tool: ToolInfo, status: dict) -> str:
        """
        Format tool installation status.
        
        Args:
            tool: ToolInfo object
            status: Installation status dictionary
            
        Returns:
            Formatted installation status string
        """
        try:
            lines = []
            
            # Header
            tool_name = self._colorize(tool.name, 'bold')
            lines.append(f"Installation Status: {tool_name}")
            lines.append(self._create_separator(30))
            
            # Status information
            install_status = status.get('status', 'unknown')
            
            if install_status == 'installed':
                status_text = self._colorize(f"{self.symbols['check']} Installed", 'green')
            elif install_status == 'not_installed':
                status_text = self._colorize(f"{self.symbols['cross']} Not Installed", 'red')
            elif install_status == 'installing':
                status_text = self._colorize(f"{self.symbols['download']} Installing...", 'yellow')
            else:
                status_text = self._colorize(f"{self.symbols['warning']} {install_status}", 'yellow')
            
            lines.append(f"Status: {status_text}")
            
            # Additional status details
            if 'install_path' in status:
                lines.append(f"Path: {status['install_path']}")
            
            if 'version' in status:
                lines.append(f"Version: {status['version']}")
            
            if 'install_date' in status:
                lines.append(f"Installed: {status['install_date']}")
            
            if 'last_used' in status:
                lines.append(f"Last Used: {status['last_used']}")
            
            # Error information
            if 'error' in status:
                lines.append("")
                error_text = self._colorize(f"{self.symbols['warning']} Error: {status['error']}", 'red')
                lines.append(error_text)
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error formatting installation status: {e}")
            return f"Error displaying installation status for {tool.name}"
    
    def display_tool_dependencies(self, tool: ToolInfo) -> str:
        """
        Display tool dependencies information.
        
        Args:
            tool: ToolInfo object
            
        Returns:
            Formatted dependencies string
        """
        try:
            dependencies = getattr(tool, 'dependencies', [])
            if not dependencies:
                return self._colorize("No dependencies required", 'green')
            
            lines = []
            lines.append(self._colorize("Dependencies:", 'bold'))
            
            for i, dep in enumerate(dependencies, 1):
                if isinstance(dep, dict):
                    dep_name = dep.get('name', 'Unknown')
                    dep_version = dep.get('version', 'Any')
                    dep_required = dep.get('required', True)
                    
                    req_text = "Required" if dep_required else "Optional"
                    req_color = 'red' if dep_required else 'yellow'
                    
                    dep_line = f"  {i}. {dep_name} ({dep_version}) - {self._colorize(req_text, req_color)}"
                else:
                    dep_line = f"  {i}. {dep}"
                
                lines.append(dep_line)
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error displaying dependencies: {e}")
            return "Error displaying dependencies"
    
    def display_tool_screenshots(self, tool: ToolInfo) -> str:
        """
        Display tool screenshots information.
        
        Args:
            tool: ToolInfo object
            
        Returns:
            Formatted screenshots information
        """
        try:
            screenshots = getattr(tool, 'screenshots', [])
            if not screenshots:
                return self._colorize("No screenshots available", 'dim')
            
            lines = []
            lines.append(self._colorize("Screenshots:", 'bold'))
            
            for i, screenshot in enumerate(screenshots, 1):
                if isinstance(screenshot, dict):
                    title = screenshot.get('title', f'Screenshot {i}')
                    url = screenshot.get('url', '')
                    description = screenshot.get('description', '')
                    
                    screen_line = f"  {i}. {title}"
                    if description:
                        screen_line += f" - {description}"
                    
                    lines.append(screen_line)
                    
                    if url:
                        lines.append(f"     URL: {self._colorize(url, 'blue')}")
                else:
                    lines.append(f"  {i}. {screenshot}")
            
            return "\n".join(lines)
            
        except Exception as e:
            log_error(f"Error displaying screenshots: {e}")
            return "Error displaying screenshots"
    
    def format_trust_score(self, score: float) -> str:
        """
        Format trust score with visual indicators.
        
        Args:
            score: Trust score (0.0 to 10.0)
            
        Returns:
            Formatted trust score string
        """
        try:
            if score >= 9.0:
                color = 'green'
                level = 'Excellent'
                stars = '★★★★★'
            elif score >= 7.0:
                color = 'green'
                level = 'Good'
                stars = '★★★★☆'
            elif score >= 5.0:
                color = 'yellow'
                level = 'Average'
                stars = '★★★☆☆'
            elif score >= 3.0:
                color = 'yellow'
                level = 'Below Average'
                stars = '★★☆☆☆'
            else:
                color = 'red'
                level = 'Poor'
                stars = '★☆☆☆☆'
            
            score_text = f"{score:.1f}/10.0"
            formatted_score = self._colorize(f"{self.symbols['trust']} {score_text} ({level})", color)
            
            return f"{formatted_score} {stars}"
            
        except Exception as e:
            log_error(f"Error formatting trust score: {e}")
            return f"Trust: {score:.1f}/10.0"
    
    def _format_tool_header(self, tool: ToolInfo) -> str:
        """Format tool header with name and key information."""
        try:
            name = self._colorize(tool.name, 'bold')
            version = getattr(tool, 'version', '1.0.0')
            category = getattr(tool, 'category', 'General')
            
            # Add status indicators
            indicators = []
            
            if getattr(tool, 'verified', False):
                indicators.append(self._colorize(f"{self.symbols['verified']} Verified", 'green'))
            
            if getattr(tool, 'new', False):
                indicators.append(self._colorize(f"{self.symbols['new']} New", 'cyan'))
            
            if getattr(tool, 'updated', False):
                indicators.append(self._colorize(f"{self.symbols['updated']} Updated", 'blue'))
            
            # Build header line
            header_parts = [f"{name} v{version}"]
            
            if indicators:
                header_parts.append(" | ".join(indicators))
            
            header_line = " | ".join(header_parts)
            
            # Add category
            category_line = self._colorize(f"{self.symbols['category']} {category}", 'dim')
            
            return f"{header_line}\n{category_line}"
            
        except Exception as e:
            log_error(f"Error formatting tool header: {e}")
            return f"{tool.name}"
    
    def _format_basic_info(self, tool: ToolInfo) -> List[str]:
        """Format basic tool information."""
        lines = []
        
        try:
            # Description
            description = getattr(tool, 'description', 'No description available')
            wrapped_desc = self._wrap_text(description, self.max_description_length)
            lines.append(f"Description: {wrapped_desc}")
            
            # Author
            author = getattr(tool, 'author', 'Unknown')
            lines.append(f"{self.symbols['author']} Author: {author}")
            
            # Size
            size = getattr(tool, 'size', 0)
            size_str = self._format_file_size(size)
            lines.append(f"{self.symbols['size']} Size: {size_str}")
            
            # Platforms
            platforms = getattr(tool, 'platforms', ['windows'])
            if isinstance(platforms, str):
                platforms = [platforms]
            platforms_str = ", ".join(platforms)
            lines.append(f"{self.symbols['platform']} Platforms: {platforms_str}")
            
            # Trust score
            trust_score = getattr(tool, 'trust_score', 5.0)
            trust_str = self.format_trust_score(trust_score)
            lines.append(trust_str)
            
        except Exception as e:
            log_error(f"Error formatting basic info: {e}")
            lines.append("Error displaying basic information")
        
        return lines
    
    def _format_detailed_info(self, tool: ToolInfo) -> List[str]:
        """Format detailed tool information."""
        lines = []
        
        try:
            # Tags
            tags = getattr(tool, 'tags', [])
            if tags:
                if isinstance(tags, str):
                    tags = [tags]
                tags_str = ", ".join(tags)
                lines.append(f"Tags: {self._colorize(tags_str, 'cyan')}")
            
            # Dependencies
            dependencies_str = self.display_tool_dependencies(tool)
            lines.append(dependencies_str)
            
            # Screenshots
            screenshots_str = self.display_tool_screenshots(tool)
            lines.append(screenshots_str)
            
            # Additional metadata
            date_added = getattr(tool, 'date_added', None)
            if date_added:
                lines.append(f"Date Added: {date_added}")
            
            last_updated = getattr(tool, 'last_updated', None)
            if last_updated:
                lines.append(f"Last Updated: {last_updated}")
            
        except Exception as e:
            log_error(f"Error formatting detailed info: {e}")
            lines.append("Error displaying detailed information")
        
        return lines
    
    def _format_tool_actions(self, tool: ToolInfo) -> str:
        """Format available actions for the tool."""
        try:
            actions = [
                "Actions:",
                "  [I] Install",
                "  [V] View Details",
                "  [F] Add to Favorites",
                "  [D] Download Only",
                "  [C] Compare with Others"
            ]
            
            return "\n".join(actions)
            
        except Exception as e:
            log_error(f"Error formatting tool actions: {e}")
            return "Actions: [I] Install | [V] View | [F] Favorite"
    
    def _format_tool_list_item(self, tool: ToolInfo, index: int) -> str:
        """Format a single tool item in a list."""
        try:
            # Basic info
            name = self._colorize(tool.name, 'bold')
            category = getattr(tool, 'category', 'General')
            size = self._format_file_size(getattr(tool, 'size', 0))
            trust_score = getattr(tool, 'trust_score', 5.0)
            
            # Trust indicator
            if trust_score >= 8.0:
                trust_indicator = self._colorize('●', 'green')
            elif trust_score >= 5.0:
                trust_indicator = self._colorize('●', 'yellow')
            else:
                trust_indicator = self._colorize('●', 'red')
            
            # Status indicators
            status_indicators = []
            if getattr(tool, 'verified', False):
                status_indicators.append(self._colorize('✓', 'green'))
            if getattr(tool, 'new', False):
                status_indicators.append(self._colorize('N', 'cyan'))
            
            status_str = " ".join(status_indicators) if status_indicators else ""
            
            # Format line
            line_parts = [
                f"{index:2d}.",
                name,
                f"({category})",
                f"[{size}]",
                trust_indicator,
                status_str
            ]
            
            # Remove empty parts
            line_parts = [part for part in line_parts if part.strip()]
            
            return " ".join(line_parts)
            
        except Exception as e:
            log_error(f"Error formatting tool list item: {e}")
            return f"{index:2d}. {tool.name} (Error displaying info)"
    
    def _format_search_result_item(self, tool: ToolInfo, index: int, query: str) -> str:
        """Format a search result item with query highlighting."""
        try:
            base_item = self._format_tool_list_item(tool, index)
            
            # Highlight query terms (simple text replacement)
            if query and len(query) > 2:
                query_lower = query.lower()
                highlighted_query = self._colorize(query, 'yellow', background=True)
                
                # Replace query occurrences (case-insensitive)
                import re
                pattern = re.compile(re.escape(query), re.IGNORECASE)
                base_item = pattern.sub(highlighted_query, base_item)
            
            return base_item
            
        except Exception as e:
            log_error(f"Error formatting search result item: {e}")
            return self._format_tool_list_item(tool, index)
    
    def _prepare_comparison_data(self, tools: List[ToolInfo]) -> Dict[str, List[str]]:
        """Prepare data for comparison table."""
        try:
            data = {
                'Name': [],
                'Category': [],
                'Size': [],
                'Trust': [],
                'Platforms': [],
                'Author': []
            }
            
            for tool in tools:
                data['Name'].append(tool.name)
                data['Category'].append(getattr(tool, 'category', 'General'))
                data['Size'].append(self._format_file_size(getattr(tool, 'size', 0)))
                data['Trust'].append(f"{getattr(tool, 'trust_score', 5.0):.1f}")
                
                platforms = getattr(tool, 'platforms', ['windows'])
                if isinstance(platforms, str):
                    platforms = [platforms]
                data['Platforms'].append(", ".join(platforms))
                
                data['Author'].append(getattr(tool, 'author', 'Unknown'))
            
            return data
            
        except Exception as e:
            log_error(f"Error preparing comparison data: {e}")
            return {}
    
    def _format_comparison_table_rows(self, data: Dict[str, List[str]]) -> List[str]:
        """Format comparison table rows."""
        try:
            if not data:
                return ["No data to display"]
            
            lines = []
            
            # Calculate column widths
            col_widths = {}
            for key, values in data.items():
                max_width = max(len(str(value)) for value in values + [key])
                col_widths[key] = min(max_width + 2, 20)  # Limit column width
            
            # Header row
            header_parts = []
            for key in data.keys():
                header_parts.append(key.ljust(col_widths[key]))
            
            header_line = " | ".join(header_parts)
            lines.append(self._colorize(header_line, 'bold'))
            
            # Separator
            separator_parts = []
            for key in data.keys():
                separator_parts.append("-" * col_widths[key])
            
            separator_line = "-+-".join(separator_parts)
            lines.append(separator_line)
            
            # Data rows
            num_rows = len(next(iter(data.values())))
            for i in range(num_rows):
                row_parts = []
                for key, values in data.items():
                    value = str(values[i])
                    if len(value) > col_widths[key] - 2:
                        value = value[:col_widths[key] - 5] + "..."
                    row_parts.append(value.ljust(col_widths[key]))
                
                row_line = " | ".join(row_parts)
                lines.append(row_line)
            
            return lines
            
        except Exception as e:
            log_error(f"Error formatting comparison table: {e}")
            return ["Error formatting comparison table"]
    
    def _format_file_size(self, size: Union[int, str]) -> str:
        """Format file size in human-readable format."""
        try:
            if isinstance(size, str):
                return size
            
            if size == 0:
                return "Unknown"
            
            units = ['B', 'KB', 'MB', 'GB', 'TB']
            size_float = float(size)
            
            for unit in units:
                if size_float < 1024.0:
                    if unit == 'B':
                        return f"{int(size_float)} {unit}"
                    else:
                        return f"{size_float:.1f} {unit}"
                size_float /= 1024.0
            
            return f"{size_float:.1f} PB"  # Petabytes
            
        except Exception as e:
            log_error(f"Error formatting file size: {e}")
            return "Unknown"
    
    def _wrap_text(self, text: str, max_length: int) -> str:
        """Wrap text to specified length."""
        try:
            if len(text) <= max_length:
                return text
            
            # Find last space before max_length
            wrap_pos = text.rfind(' ', 0, max_length)
            if wrap_pos == -1:
                wrap_pos = max_length
            
            return text[:wrap_pos] + "..."
            
        except Exception as e:
            log_error(f"Error wrapping text: {e}")
            return text
    
    def _create_separator(self, length: Optional[int] = None) -> str:
        """Create a separator line."""
        try:
            if length is None:
                length = min(self.console_width, 80)
            
            return "─" * length
            
        except Exception as e:
            log_error(f"Error creating separator: {e}")
            return "-" * 50
    
    def _colorize(self, text: str, color: str, background: bool = False) -> str:
        """
        Apply color to text if colors are enabled.
        
        Args:
            text: Text to colorize
            color: Color name
            background: Apply as background color
            
        Returns:
            Colorized text or original text if colors disabled
        """
        try:
            if not self.colors_enabled or color not in self.colors:
                return text
            
            if background:
                # Simple background highlighting (not implemented for all terminals)
                return f"{self.colors.get('bold', '')}{text}{self.colors.get('reset', '')}"
            else:
                return f"{self.colors[color]}{text}{self.colors.get('reset', '')}"
            
        except Exception as e:
            log_error(f"Error colorizing text: {e}")
            return text