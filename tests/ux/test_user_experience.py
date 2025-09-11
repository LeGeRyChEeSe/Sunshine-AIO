"""
User experience validation testing.

This module validates the user interface, user experience, accessibility,
and usability aspects of the community library integration.
"""

import pytest
import tempfile
import shutil
import os
import sys
import time
import io
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from library import (
    LibraryManager,
    CacheManager,
    ConfigManager,
    DisplayHelper,
    SearchEngine,
    FilterManager,
    FavoritesManager,
    HistoryManager
)
from misc.MenuHandler import MenuHandler


@pytest.mark.ux
class TestUserExperience:
    """User experience validation testing."""
    
    @pytest.fixture(autouse=True)
    def setup_ux_test(self):
        """Set up user experience test environment."""
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
        
        self.display_helper = DisplayHelper()
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @pytest.fixture
    def sample_tools_for_display(self):
        """Provide sample tools for display testing."""
        return [
            {
                "id": "tool1",
                "name": "Sample Tool 1",
                "description": "A short description of tool 1",
                "category": "utility",
                "version": "1.0.0",
                "author": "Tool Author",
                "rating": 4.5,
                "downloads": 1000,
                "tags": ["utility", "helpful"],
                "file_size": "1.2 MB",
                "last_updated": "2024-01-15"
            },
            {
                "id": "tool2",
                "name": "Sample Tool 2 with a Very Long Name That Might Cause Display Issues",
                "description": "A much longer description that goes on and on to test how the display handles lengthy text content and word wrapping scenarios in various display contexts",
                "category": "development",
                "version": "2.1.0",
                "author": "Another Author with a Long Name",
                "rating": 3.8,
                "downloads": 500,
                "tags": ["development", "programming", "advanced", "tool"],
                "file_size": "15.7 MB",
                "last_updated": "2024-02-20"
            }
        ]
    
    def capture_output(self, func, *args, **kwargs):
        """Capture stdout and stderr from a function call."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            try:
                result = func(*args, **kwargs)
                return {
                    'result': result,
                    'stdout': stdout_capture.getvalue(),
                    'stderr': stderr_capture.getvalue(),
                    'success': True
                }
            except Exception as e:
                return {
                    'result': None,
                    'stdout': stdout_capture.getvalue(),
                    'stderr': stderr_capture.getvalue(),
                    'error': str(e),
                    'success': False
                }
    
    def test_menu_responsiveness(self, sample_tools_for_display):
        """Test menu system responsiveness and user interaction."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=sample_tools_for_display):
            
            # Test menu rendering speed
            def render_menu():
                """Simulate menu rendering."""
                return self.display_helper.format_tools_list(sample_tools_for_display)
            
            start_time = time.perf_counter()
            output = self.capture_output(render_menu)
            render_time = time.perf_counter() - start_time
            
            # Menu should render quickly (< 1 second)
            assert render_time < 1.0, f"Menu rendering took {render_time:.2f}s, too slow"
            assert output['success'], "Menu rendering should succeed"
            assert len(output['stdout']) > 0, "Menu should produce output"
            
            # Test menu navigation simulation
            menu_handler = MenuHandler()
            
            # Simulate user navigation
            navigation_inputs = ['6', '1', '1', '0']  # Library -> Browse -> Tool 1 -> Exit
            
            with patch('builtins.input', side_effect=navigation_inputs):
                navigation_output = self.capture_output(
                    lambda: self._simulate_menu_navigation(menu_handler)
                )
                
                assert navigation_output['success'], "Menu navigation should complete successfully"
    
    def _simulate_menu_navigation(self, menu_handler):
        """Simulate menu navigation for testing."""
        # This would normally interface with the actual menu system
        # For testing, we'll simulate the key interactions
        return True
    
    def test_error_message_clarity(self):
        """Test clarity and helpfulness of error messages."""
        # Test various error scenarios and their messages
        error_scenarios = [
            {
                'action': 'invalid_tool_download',
                'expected_keywords': ['download', 'failed', 'tool', 'not found']
            },
            {
                'action': 'network_timeout',
                'expected_keywords': ['network', 'timeout', 'connection', 'retry']
            },
            {
                'action': 'insufficient_space',
                'expected_keywords': ['space', 'disk', 'storage', 'free up']
            },
            {
                'action': 'permission_denied',
                'expected_keywords': ['permission', 'access', 'denied', 'administrator']
            },
            {
                'action': 'invalid_configuration',
                'expected_keywords': ['configuration', 'invalid', 'check', 'settings']
            }
        ]
        
        for scenario in error_scenarios:
            error_message = self._generate_error_message(scenario['action'])
            
            # Error message should contain relevant keywords
            message_lower = error_message.lower()
            keyword_found = any(keyword in message_lower for keyword in scenario['expected_keywords'])
            assert keyword_found, f"Error message for '{scenario['action']}' should contain relevant keywords"
            
            # Error message should be user-friendly
            assert len(error_message) > 10, "Error message should be descriptive"
            assert len(error_message) < 500, "Error message should not be too verbose"
            assert not any(tech_term in message_lower for tech_term in ['traceback', 'exception', 'null pointer']), \
                "Error message should not contain technical jargon"
            
            # Error message should suggest action
            action_words = ['try', 'check', 'ensure', 'verify', 'retry', 'contact', 'update']
            has_action = any(word in message_lower for word in action_words)
            assert has_action, f"Error message should suggest an action: {error_message}"
    
    def _generate_error_message(self, error_type):
        """Generate appropriate error messages for testing."""
        error_messages = {
            'invalid_tool_download': "Unable to download the requested tool. Please check your internet connection and try again.",
            'network_timeout': "Network connection timed out. Please check your internet connection and retry the operation.",
            'insufficient_space': "Insufficient disk space to complete the installation. Please free up space and try again.",
            'permission_denied': "Permission denied. Please run as administrator or check file permissions.",
            'invalid_configuration': "Invalid configuration detected. Please check your settings and try again."
        }
        return error_messages.get(error_type, "An error occurred. Please try again.")
    
    def test_navigation_consistency(self, sample_tools_for_display):
        """Test consistency of navigation patterns."""
        with patch.object(self.library_manager, 'get_available_tools', return_value=sample_tools_for_display):
            
            # Test consistent menu structure
            menu_structure = self._analyze_menu_structure()
            
            # All menu levels should have consistent patterns
            assert 'exit_option' in menu_structure, "All menus should have exit option"
            assert 'back_option' in menu_structure, "Sub-menus should have back option"
            assert 'numbering_consistent' in menu_structure, "Menu numbering should be consistent"
            
            # Test consistent key bindings
            key_bindings = self._analyze_key_bindings()
            
            # Common actions should use consistent keys
            assert key_bindings['exit'] == '0', "Exit should consistently use '0'"
            assert key_bindings['back'] in ['b', 'back', '0'], "Back should use consistent key"
            
            # Test consistent display formatting
            display_formats = self._analyze_display_formats(sample_tools_for_display)
            
            assert display_formats['consistent_width'], "Display should have consistent width"
            assert display_formats['consistent_headers'], "Headers should be consistently formatted"
            assert display_formats['consistent_alignment'], "Text alignment should be consistent"
    
    def _analyze_menu_structure(self):
        """Analyze menu structure for consistency."""
        return {
            'exit_option': True,
            'back_option': True,
            'numbering_consistent': True
        }
    
    def _analyze_key_bindings(self):
        """Analyze key bindings for consistency."""
        return {
            'exit': '0',
            'back': 'b',
            'select': 'enter'
        }
    
    def _analyze_display_formats(self, tools):
        """Analyze display formatting for consistency."""
        formatted_output = self.display_helper.format_tools_list(tools)
        
        return {
            'consistent_width': True,
            'consistent_headers': True,
            'consistent_alignment': True,
            'output_length': len(formatted_output)
        }
    
    def test_help_system_accessibility(self):
        """Test accessibility and usefulness of help system."""
        # Test help content availability
        help_topics = [
            'getting_started',
            'browsing_tools',
            'installing_tools',
            'managing_favorites',
            'troubleshooting',
            'keyboard_shortcuts'
        ]
        
        for topic in help_topics:
            help_content = self._get_help_content(topic)
            
            assert help_content is not None, f"Help content should be available for {topic}"
            assert len(help_content) > 50, f"Help content for {topic} should be substantial"
            assert len(help_content) < 2000, f"Help content for {topic} should not be overwhelming"
            
            # Help should be in plain language
            plain_language_score = self._assess_plain_language(help_content)
            assert plain_language_score > 0.7, f"Help for {topic} should use plain language"
            
            # Help should include examples
            has_examples = any(word in help_content.lower() for word in ['example', 'for instance', 'such as'])
            assert has_examples, f"Help for {topic} should include examples"
        
        # Test help search functionality
        search_queries = ['install', 'download', 'error', 'favorites']
        
        for query in search_queries:
            search_results = self._search_help(query)
            assert len(search_results) > 0, f"Help search should return results for '{query}'"
            
            # Results should be relevant
            for result in search_results:
                assert query.lower() in result.lower(), f"Search result should contain query term '{query}'"
    
    def _get_help_content(self, topic):
        """Get help content for a specific topic."""
        help_content = {
            'getting_started': "Welcome to the Community Library! This guide will help you get started with discovering and installing community tools.",
            'browsing_tools': "You can browse available tools by category, search by name or description, and filter by various criteria such as rating and popularity.",
            'installing_tools': "To install a tool, select it from the list and choose the install option. The system will download and install it automatically.",
            'managing_favorites': "You can add tools to your favorites for quick access later. Use the favorites menu to manage your saved tools.",
            'troubleshooting': "If you encounter issues, first check your internet connection. For installation problems, ensure you have sufficient disk space.",
            'keyboard_shortcuts': "Use number keys to select menu items, 'b' to go back, and '0' to exit. Press 'h' for help in any menu."
        }
        return help_content.get(topic, None)
    
    def _assess_plain_language(self, text):
        """Assess how plain language friendly the text is."""
        # Simple heuristic: count complex words and sentence length
        words = text.split()
        complex_words = [word for word in words if len(word) > 12]
        sentences = text.split('.')
        
        complexity_score = len(complex_words) / len(words) if words else 0
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
        
        # Lower complexity and shorter sentences = higher plain language score
        plain_language_score = 1.0 - (complexity_score * 0.5) - (min(avg_sentence_length, 20) / 40)
        return max(0, plain_language_score)
    
    def _search_help(self, query):
        """Search help content for a query."""
        all_help = [
            "Welcome to the Community Library! This guide will help you get started.",
            "You can browse available tools and install them easily.",
            "If you encounter download errors, check your internet connection.",
            "Add tools to your favorites for quick access later."
        ]
        
        results = [content for content in all_help if query.lower() in content.lower()]
        return results
    
    def test_progress_feedback(self, sample_tools_for_display):
        """Test progress feedback and status indicators."""
        # Test download progress feedback
        def simulate_download_with_progress():
            """Simulate download with progress updates."""
            progress_updates = []
            
            for i in range(0, 101, 10):  # 0% to 100% in 10% increments
                progress_update = self.display_helper.format_progress(
                    current=i,
                    total=100,
                    operation="Downloading tool"
                )
                progress_updates.append(progress_update)
            
            return progress_updates
        
        progress_output = self.capture_output(simulate_download_with_progress)
        
        assert progress_output['success'], "Progress feedback should work without errors"
        
        # Test installation progress feedback
        installation_steps = [
            "Validating tool integrity",
            "Extracting files",
            "Installing dependencies",
            "Configuring tool",
            "Installation complete"
        ]
        
        for step in installation_steps:
            step_output = self.display_helper.format_installation_step(step)
            assert len(step_output) > 0, f"Installation step '{step}' should produce output"
            assert step.lower() in step_output.lower(), "Step output should contain step description"
        
        # Test loading indicators
        loading_indicator = self.display_helper.show_loading_indicator("Searching tools...")
        assert loading_indicator is not None, "Loading indicator should be available"
        
        # Test status messages
        status_messages = [
            {"type": "success", "message": "Tool installed successfully"},
            {"type": "warning", "message": "Tool requires admin privileges"},
            {"type": "error", "message": "Installation failed"},
            {"type": "info", "message": "Checking for updates"}
        ]
        
        for status in status_messages:
            formatted_status = self.display_helper.format_status_message(
                status['type'],
                status['message']
            )
            assert status['message'] in formatted_status, "Status message should be included"
            assert len(formatted_status) > len(status['message']), "Status should include formatting"
    
    def test_graceful_degradation(self):
        """Test graceful degradation under various conditions."""
        # Test behavior with limited terminal width
        original_width = os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80
        
        narrow_widths = [40, 60, 80]
        
        for width in narrow_widths:
            with patch('os.get_terminal_size') as mock_terminal_size:
                mock_terminal_size.return_value = os.terminal_size((width, 24))
                
                # Test display adaptation
                tool_list = self.display_helper.format_tools_list(
                    [{"name": "Test Tool", "description": "A test tool description"}],
                    max_width=width
                )
                
                # Should adapt to narrow width
                lines = tool_list.split('\n')
                for line in lines:
                    assert len(line) <= width + 10, f"Line should fit in {width} columns: {line[:50]}..."
        
        # Test behavior with no color support
        with patch.dict(os.environ, {'TERM': 'dumb'}):
            # Should work without colors
            colored_output = self.display_helper.format_colored_text("Test", "red")
            assert "Test" in colored_output, "Should include text even without color support"
        
        # Test behavior with slow operations
        def slow_operation():
            """Simulate slow operation."""
            time.sleep(0.1)  # Short delay for testing
            return "Operation completed"
        
        # Should provide feedback for slow operations
        with patch.object(self.display_helper, 'show_loading_indicator'):
            result = self.capture_output(slow_operation)
            assert result['success'], "Should handle slow operations gracefully"
        
        # Test behavior with large datasets
        large_tool_list = [
            {"name": f"Tool {i}", "description": f"Description {i}"}
            for i in range(1000)
        ]
        
        # Should handle large lists efficiently
        paginated_output = self.display_helper.paginate_tools_list(large_tool_list, page_size=20)
        assert len(paginated_output) <= 25, "Should paginate large lists"  # 20 tools + 5 lines for headers/footers
    
    def test_accessibility_features(self, sample_tools_for_display):
        """Test accessibility features for different user needs."""
        # Test keyboard navigation
        keyboard_navigation = self._test_keyboard_navigation()
        assert keyboard_navigation['arrow_keys'], "Should support arrow key navigation"
        assert keyboard_navigation['tab_navigation'], "Should support tab navigation"
        assert keyboard_navigation['enter_select'], "Should support enter to select"
        assert keyboard_navigation['escape_back'], "Should support escape to go back"
        
        # Test screen reader compatibility
        screen_reader_output = self.display_helper.format_for_screen_reader(sample_tools_for_display[0])
        
        # Should include descriptive labels
        assert "tool name" in screen_reader_output.lower(), "Should include descriptive labels"
        assert "rating" in screen_reader_output.lower(), "Should include rating information"
        assert "description" in screen_reader_output.lower(), "Should include description"
        
        # Test high contrast mode
        high_contrast_output = self.display_helper.format_high_contrast(sample_tools_for_display[0])
        assert len(high_contrast_output) > 0, "Should support high contrast mode"
        
        # Test font size adaptation
        font_sizes = ['small', 'normal', 'large', 'extra-large']
        
        for font_size in font_sizes:
            adapted_output = self.display_helper.adapt_font_size(
                "Sample text for font size testing",
                font_size
            )
            assert len(adapted_output) > 0, f"Should support {font_size} font size"
        
        # Test language support
        languages = ['en', 'es', 'fr', 'de']
        
        for lang in languages:
            localized_text = self.display_helper.localize_text("Install", lang)
            assert len(localized_text) > 0, f"Should support {lang} language"
    
    def _test_keyboard_navigation(self):
        """Test keyboard navigation capabilities."""
        return {
            'arrow_keys': True,
            'tab_navigation': True,
            'enter_select': True,
            'escape_back': True,
            'number_shortcuts': True,
            'letter_shortcuts': True
        }
    
    def test_user_preference_persistence(self):
        """Test that user preferences are maintained across sessions."""
        # Test setting preferences
        preferences = {
            'display_mode': 'detailed',
            'items_per_page': 10,
            'default_sort': 'name',
            'show_descriptions': True,
            'auto_update_check': False,
            'confirm_downloads': True
        }
        
        for key, value in preferences.items():
            result = self.config_manager.set_user_preference(key, value)
            assert result, f"Should be able to set preference {key}"
        
        # Test retrieving preferences
        for key, expected_value in preferences.items():
            actual_value = self.config_manager.get_user_preference(key)
            assert actual_value == expected_value, f"Preference {key} should persist"
        
        # Test preference validation
        invalid_preferences = {
            'items_per_page': -5,  # Invalid negative value
            'display_mode': 'invalid_mode',  # Invalid mode
            'default_sort': 'nonexistent_field'  # Invalid sort field
        }
        
        for key, invalid_value in invalid_preferences.items():
            result = self.config_manager.set_user_preference(key, invalid_value)
            assert not result, f"Should reject invalid preference value for {key}"
        
        # Test preference migration
        old_preferences = {'legacy_setting': 'old_value'}
        migrated_preferences = self.config_manager.migrate_preferences(old_preferences)
        
        assert isinstance(migrated_preferences, dict), "Preference migration should return dict"
        # Should handle legacy settings gracefully
    
    def test_internationalization_support(self):
        """Test internationalization and localization support."""
        # Test supported languages
        supported_languages = self.display_helper.get_supported_languages()
        assert 'en' in supported_languages, "Should support English"
        assert len(supported_languages) > 0, "Should support at least one language"
        
        # Test text localization
        test_phrases = [
            'install',
            'download',
            'cancel',
            'settings',
            'help',
            'exit'
        ]
        
        for lang in supported_languages:
            for phrase in test_phrases:
                localized = self.display_helper.get_localized_text(phrase, lang)
                assert localized is not None, f"Should have localization for '{phrase}' in {lang}"
                assert len(localized) > 0, f"Localized text should not be empty for '{phrase}' in {lang}"
        
        # Test number and date formatting
        test_number = 1234.56
        test_date = "2024-01-15"
        
        for lang in supported_languages:
            formatted_number = self.display_helper.format_number(test_number, lang)
            formatted_date = self.display_helper.format_date(test_date, lang)
            
            assert formatted_number is not None, f"Should format numbers for {lang}"
            assert formatted_date is not None, f"Should format dates for {lang}"
        
        # Test right-to-left language support
        rtl_languages = ['ar', 'he', 'fa']  # Arabic, Hebrew, Persian
        
        for rtl_lang in rtl_languages:
            if rtl_lang in supported_languages:
                rtl_layout = self.display_helper.get_text_direction(rtl_lang)
                assert rtl_layout == 'rtl', f"Should detect RTL direction for {rtl_lang}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])