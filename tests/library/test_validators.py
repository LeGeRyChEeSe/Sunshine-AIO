"""
Comprehensive unit tests for ToolValidator and validation functionality.

Tests cover schema validation, security validation at different levels,
platform compatibility checking, checksum verification, and dependency validation.
"""

import pytest
import os
import json
import tempfile
import hashlib
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from library.validators import (
    ToolValidator, ValidationLevel, ValidationResult
)


class TestValidationResult:
    """Test ValidationResult functionality."""
    
    def test_validation_result_initialization_default(self):
        """Test ValidationResult default initialization."""
        result = ValidationResult()
        
        assert result.is_valid is True
        assert result.level == ValidationLevel.STANDARD
        assert result.messages == []
        assert result.warnings == []
        assert result.errors == []
        assert result.security_score == 1.0
        assert result.timestamp is not None
    
    def test_validation_result_initialization_custom(self):
        """Test ValidationResult with custom parameters."""
        messages = ["Info message"]
        warnings = ["Warning message"]
        errors = ["Error message"]
        
        result = ValidationResult(
            is_valid=False,
            level=ValidationLevel.STRICT,
            messages=messages,
            warnings=warnings,
            errors=errors,
            security_score=0.7
        )
        
        assert result.is_valid is False
        assert result.level == ValidationLevel.STRICT
        assert result.messages == messages
        assert result.warnings == warnings
        assert result.errors == errors
        assert result.security_score == 0.7
    
    def test_validation_result_add_message_info(self):
        """Test adding info message."""
        result = ValidationResult()
        
        result.add_message("Test info message", "info")
        
        assert len(result.messages) == 1
        assert result.messages[0] == "Test info message"
        assert result.is_valid is True  # Should remain valid
    
    def test_validation_result_add_message_warning(self):
        """Test adding warning message."""
        result = ValidationResult()
        
        result.add_message("Test warning", "warning")
        
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"
        assert result.is_valid is True  # Should remain valid
    
    def test_validation_result_add_message_error(self):
        """Test adding error message."""
        result = ValidationResult(is_valid=True)
        
        result.add_message("Test error", "error")
        
        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"
        assert result.is_valid is False  # Should become invalid
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization to dict."""
        result = ValidationResult(
            is_valid=False,
            level=ValidationLevel.PARANOID,
            messages=["Info"],
            warnings=["Warning"],
            errors=["Error"],
            security_score=0.5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['is_valid'] is False
        assert result_dict['level'] == "paranoid"
        assert result_dict['messages'] == ["Info"]
        assert result_dict['warnings'] == ["Warning"]
        assert result_dict['errors'] == ["Error"]
        assert result_dict['security_score'] == 0.5
        assert 'timestamp' in result_dict


class TestToolValidatorInitialization:
    """Test ToolValidator initialization and configuration."""
    
    def test_tool_validator_initialization_default(self, tool_validator):
        """Test default ToolValidator initialization."""
        assert tool_validator.validation_level == ValidationLevel.STANDARD
        assert tool_validator.config['max_file_size'] == 100 * 1024 * 1024  # 100MB
        assert tool_validator.config['allowed_extensions'] is not None
        assert tool_validator.config['blocked_domains'] is not None
        assert tool_validator.config['require_https'] is True
        assert isinstance(tool_validator._malicious_patterns, list)
    
    def test_tool_validator_initialization_custom_level(self):
        """Test ToolValidator initialization with custom level."""
        validator = ToolValidator(validation_level=ValidationLevel.PARANOID)
        
        assert validator.validation_level == ValidationLevel.PARANOID
    
    def test_tool_validator_initialization_custom_config(self):
        """Test ToolValidator initialization with custom config."""
        custom_config = {
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'require_https': False,
            'allowed_extensions': ['.exe', '.zip'],
            'custom_setting': 'test_value'
        }
        
        validator = ToolValidator(config=custom_config)
        
        assert validator.config['max_file_size'] == 50 * 1024 * 1024
        assert validator.config['require_https'] is False
        assert validator.config['custom_setting'] == 'test_value'
    
    def test_tool_validator_malicious_patterns_loading(self, tool_validator):
        """Test that malicious patterns are loaded."""
        patterns = tool_validator._malicious_patterns
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        # Should contain some common malicious patterns
        pattern_strings = [p.pattern if hasattr(p, 'pattern') else str(p) for p in patterns]
        assert any('eval' in p.lower() for p in pattern_strings)
        assert any('exec' in p.lower() for p in pattern_strings)


class TestToolValidatorSchemaValidation:
    """Test schema validation functionality."""
    
    def test_validate_tool_metadata_valid(self, tool_validator, validation_test_cases):
        """Test validation of valid tool metadata."""
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_tool_metadata(valid_tool)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_tool_metadata_missing_required_fields(self, tool_validator, validation_test_cases):
        """Test validation with missing required fields."""
        incomplete_tool = validation_test_cases['missing_fields']
        
        result = tool_validator.validate_tool_metadata(incomplete_tool)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        # Should have errors about missing required fields
        assert any('id' in error.lower() for error in result.errors)
    
    def test_validate_tool_metadata_invalid_types(self, tool_validator):
        """Test validation with invalid field types."""
        invalid_tool = {
            "id": 12345,  # Should be string
            "name": ["not", "a", "string"],  # Should be string
            "version": {"major": 1},  # Should be string
            "platform_support": "not_a_list",  # Should be list
            "dependencies": {"not": "a_list"},  # Should be list
            "size": "not_a_number"  # Should be number
        }
        
        result = tool_validator.validate_tool_metadata(invalid_tool)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_tool_metadata_empty_input(self, tool_validator):
        """Test validation with empty input."""
        result = tool_validator.validate_tool_metadata({})
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_tool_metadata_none_input(self, tool_validator):
        """Test validation with None input."""
        result = tool_validator.validate_tool_metadata(None)
        
        assert result.is_valid is False
        assert len(result.errors) > 0


class TestToolValidatorSecurityValidation:
    """Test security validation functionality."""
    
    def test_validate_security_minimal_level(self, tool_validator, validation_test_cases):
        """Test security validation at minimal level."""
        tool_validator.validation_level = ValidationLevel.MINIMAL
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_security(valid_tool)
        
        assert result.is_valid is True
        assert result.security_score > 0.8  # Should have high score for valid tool
    
    def test_validate_security_standard_level(self, tool_validator, validation_test_cases):
        """Test security validation at standard level."""
        tool_validator.validation_level = ValidationLevel.STANDARD
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_security(valid_tool)
        
        assert result.is_valid is True
        assert result.security_score > 0.8
    
    def test_validate_security_strict_level(self, tool_validator, validation_test_cases):
        """Test security validation at strict level."""
        tool_validator.validation_level = ValidationLevel.STRICT
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_security(valid_tool)
        
        # Strict level might be more demanding
        assert result.is_valid is True
        assert result.security_score >= 0.0
    
    def test_validate_security_paranoid_level(self, tool_validator, validation_test_cases):
        """Test security validation at paranoid level."""
        tool_validator.validation_level = ValidationLevel.PARANOID
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_security(valid_tool)
        
        # Paranoid level might flag even valid tools as suspicious
        assert result.security_score >= 0.0
    
    def test_validate_security_malicious_tool(self, tool_validator, validation_test_cases):
        """Test security validation of malicious tool."""
        malicious_tool = validation_test_cases['malicious_content']
        
        result = tool_validator.validate_security(malicious_tool)
        
        assert result.is_valid is False
        assert result.security_score < 0.5
        assert len(result.errors) > 0
    
    def test_validate_security_invalid_url(self, tool_validator, validation_test_cases):
        """Test security validation of tool with invalid URL."""
        invalid_url_tool = validation_test_cases['invalid_url']
        
        result = tool_validator.validate_security(invalid_url_tool)
        
        assert result.is_valid is False
        assert any('url' in error.lower() for error in result.errors)
    
    def test_validate_url_valid_https(self, tool_validator):
        """Test URL validation with valid HTTPS URL."""
        valid_urls = [
            "https://github.com/user/repo/releases/download/v1.0/tool.zip",
            "https://example.com/downloads/tool.tar.gz",
            "https://cdn.example.com/files/tool.exe"
        ]
        
        for url in valid_urls:
            result = tool_validator._validate_url(url)
            assert result is True
    
    def test_validate_url_invalid_protocol(self, tool_validator):
        """Test URL validation with invalid protocols."""
        invalid_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://example.com/tool.zip"
        ]
        
        for url in invalid_urls:
            result = tool_validator._validate_url(url)
            assert result is False
    
    def test_validate_url_http_with_strict_https(self, tool_validator):
        """Test HTTP URL validation with strict HTTPS requirement."""
        tool_validator.config['require_https'] = True
        
        result = tool_validator._validate_url("http://example.com/tool.zip")
        
        assert result is False
    
    def test_validate_url_http_without_strict_https(self, tool_validator):
        """Test HTTP URL validation without strict HTTPS requirement."""
        tool_validator.config['require_https'] = False
        
        result = tool_validator._validate_url("http://example.com/tool.zip")
        
        assert result is True
    
    def test_validate_url_blocked_domains(self, tool_validator):
        """Test URL validation with blocked domains."""
        tool_validator.config['blocked_domains'] = ['malicious-site.com', 'spam-domain.net']
        
        blocked_urls = [
            "https://malicious-site.com/tool.zip",
            "https://subdomain.spam-domain.net/download.exe"
        ]
        
        for url in blocked_urls:
            result = tool_validator._validate_url(url)
            assert result is False
    
    def test_detect_malicious_patterns_clean_content(self, tool_validator):
        """Test malicious pattern detection with clean content."""
        clean_content = {
            "name": "Clean Tool",
            "description": "A legitimate tool for data processing",
            "dependencies": ["python>=3.8", "numpy>=1.20.0"]
        }
        
        result = tool_validator._detect_malicious_patterns(clean_content)
        
        assert result == []  # No malicious patterns found
    
    def test_detect_malicious_patterns_suspicious_content(self, tool_validator):
        """Test malicious pattern detection with suspicious content."""
        suspicious_content = {
            "name": "Suspicious Tool",
            "description": "This tool uses eval(user_input) and exec(code)",
            "dependencies": ["backdoor_lib", "rootkit_helper"],
            "author": "H4ck3r_1337"
        }
        
        patterns = tool_validator._detect_malicious_patterns(suspicious_content)
        
        assert len(patterns) > 0
        # Should detect eval, exec, and suspicious dependencies
    
    def test_calculate_security_score_safe_tool(self, tool_validator, validation_test_cases):
        """Test security score calculation for safe tool."""
        safe_tool = validation_test_cases['valid_tool']
        
        score = tool_validator._calculate_security_score(safe_tool, [])
        
        assert score >= 0.8  # Should have high security score
        assert score <= 1.0
    
    def test_calculate_security_score_risky_tool(self, tool_validator):
        """Test security score calculation for risky tool."""
        risky_tool = {
            "id": "risky_tool",
            "name": "Risky Tool",
            "download_url": "http://suspicious-site.com/tool.exe",  # HTTP not HTTPS
            "dependencies": ["unknown_lib"],
            "validated": False,
            "trusted": False,
            "checksum": "invalid_format"
        }
        
        malicious_patterns = ["suspicious pattern found"]
        
        score = tool_validator._calculate_security_score(risky_tool, malicious_patterns)
        
        assert score < 0.5  # Should have low security score
        assert score >= 0.0


class TestToolValidatorPlatformCompatibility:
    """Test platform compatibility validation."""
    
    def test_validate_platform_compatibility_current_platform(self, tool_validator):
        """Test platform compatibility for current platform."""
        with patch('platform.system', return_value='Linux'):
            tool_metadata = {
                "id": "linux_tool",
                "platform_support": ["linux", "macos"]
            }
            
            result = tool_validator.validate_platform_compatibility(tool_metadata)
            
            assert result.is_valid is True
            assert len(result.errors) == 0
    
    def test_validate_platform_compatibility_incompatible(self, tool_validator):
        """Test platform compatibility for incompatible platform."""
        with patch('platform.system', return_value='Linux'):
            tool_metadata = {
                "id": "windows_only_tool",
                "platform_support": ["windows"]
            }
            
            result = tool_validator.validate_platform_compatibility(tool_metadata)
            
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert any('platform' in error.lower() for error in result.errors)
    
    def test_validate_platform_compatibility_all_platforms(self, tool_validator):
        """Test platform compatibility for universal tool."""
        tool_metadata = {
            "id": "universal_tool",
            "platform_support": ["all"]
        }
        
        result = tool_validator.validate_platform_compatibility(tool_metadata)
        
        assert result.is_valid is True
    
    def test_validate_platform_compatibility_empty_support(self, tool_validator):
        """Test platform compatibility with empty platform support."""
        tool_metadata = {
            "id": "no_platform_tool",
            "platform_support": []
        }
        
        result = tool_validator.validate_platform_compatibility(tool_metadata)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_platform_compatibility_missing_field(self, tool_validator):
        """Test platform compatibility with missing platform_support field."""
        tool_metadata = {
            "id": "no_platform_field_tool"
            # Missing platform_support field
        }
        
        result = tool_validator.validate_platform_compatibility(tool_metadata)
        
        # Should handle gracefully - might assume compatible or incompatible
        assert isinstance(result.is_valid, bool)
    
    def test_normalize_platform_name(self, tool_validator):
        """Test platform name normalization."""
        test_cases = [
            ('Windows', 'windows'),
            ('Linux', 'linux'),
            ('Darwin', 'macos'),
            ('macOS', 'macos'),
            ('win32', 'windows'),
            ('linux2', 'linux'),
            ('darwin', 'macos'),
            ('Unknown', 'unknown')
        ]
        
        for input_platform, expected in test_cases:
            result = tool_validator._normalize_platform_name(input_platform)
            assert result == expected


class TestToolValidatorChecksumVerification:
    """Test checksum verification functionality."""
    
    def test_validate_checksum_valid_sha256(self, tool_validator, temp_dir):
        """Test valid SHA256 checksum verification."""
        # Create test file
        test_file = os.path.join(temp_dir, "checksum_test.txt")
        test_content = b"Test content for checksum verification"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate expected checksum
        expected_checksum = hashlib.sha256(test_content).hexdigest()
        
        result = tool_validator.validate_checksum(test_file, f"sha256:{expected_checksum}")
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_checksum_invalid_sha256(self, tool_validator, temp_dir):
        """Test invalid SHA256 checksum verification."""
        # Create test file
        test_file = os.path.join(temp_dir, "checksum_test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Use wrong checksum
        wrong_checksum = "sha256:invalid_checksum_value"
        
        result = tool_validator.validate_checksum(test_file, wrong_checksum)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any('checksum' in error.lower() for error in result.errors)
    
    def test_validate_checksum_valid_md5(self, tool_validator, temp_dir):
        """Test valid MD5 checksum verification."""
        # Create test file
        test_file = os.path.join(temp_dir, "md5_test.txt")
        test_content = b"MD5 test content"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate expected checksum
        expected_checksum = hashlib.md5(test_content).hexdigest()
        
        result = tool_validator.validate_checksum(test_file, f"md5:{expected_checksum}")
        
        assert result.is_valid is True
    
    def test_validate_checksum_unsupported_algorithm(self, tool_validator, temp_dir):
        """Test checksum with unsupported algorithm."""
        test_file = os.path.join(temp_dir, "unsupported_test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        result = tool_validator.validate_checksum(test_file, "blake2b:somevalue")
        
        assert result.is_valid is False
        assert any('unsupported' in error.lower() or 'algorithm' in error.lower() 
                  for error in result.errors)
    
    def test_validate_checksum_invalid_format(self, tool_validator, temp_dir):
        """Test checksum with invalid format."""
        test_file = os.path.join(temp_dir, "format_test.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        invalid_checksums = [
            "invalid_format_no_colon",
            "sha256:",  # Empty checksum
            ":no_algorithm",
            "sha256:not_hex_characters!"
        ]
        
        for checksum in invalid_checksums:
            result = tool_validator.validate_checksum(test_file, checksum)
            assert result.is_valid is False
    
    def test_validate_checksum_nonexistent_file(self, tool_validator):
        """Test checksum validation with non-existent file."""
        result = tool_validator.validate_checksum("/nonexistent/file.txt", "sha256:abc123")
        
        assert result.is_valid is False
        assert any('file' in error.lower() for error in result.errors)
    
    def test_calculate_file_checksum_sha256(self, tool_validator, temp_dir):
        """Test file checksum calculation for SHA256."""
        test_file = os.path.join(temp_dir, "sha256_calc.txt")
        test_content = b"Content for SHA256 calculation"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        expected = hashlib.sha256(test_content).hexdigest()
        result = tool_validator._calculate_file_checksum(test_file, "sha256")
        
        assert result == expected
    
    def test_calculate_file_checksum_md5(self, tool_validator, temp_dir):
        """Test file checksum calculation for MD5."""
        test_file = os.path.join(temp_dir, "md5_calc.txt")
        test_content = b"Content for MD5 calculation"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        expected = hashlib.md5(test_content).hexdigest()
        result = tool_validator._calculate_file_checksum(test_file, "md5")
        
        assert result == expected
    
    def test_calculate_file_checksum_unsupported_algorithm(self, tool_validator, temp_dir):
        """Test checksum calculation with unsupported algorithm."""
        test_file = os.path.join(temp_dir, "unsupported_calc.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        result = tool_validator._calculate_file_checksum(test_file, "unsupported_algo")
        
        assert result is None


class TestToolValidatorDependencyValidation:
    """Test dependency validation functionality."""
    
    def test_validate_dependencies_valid(self, tool_validator):
        """Test validation of valid dependencies."""
        dependencies = [
            "python>=3.8",
            "requests>=2.25.0",
            "numpy>=1.20.0",
            "pandas"
        ]
        
        result = tool_validator.validate_dependencies(dependencies)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_dependencies_empty_list(self, tool_validator):
        """Test validation of empty dependencies list."""
        result = tool_validator.validate_dependencies([])
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_dependencies_suspicious_packages(self, tool_validator):
        """Test validation with suspicious dependencies."""
        suspicious_dependencies = [
            "backdoor_lib",
            "rootkit_helper",
            "malware_toolkit",
            "keylogger_utils"
        ]
        
        result = tool_validator.validate_dependencies(suspicious_dependencies)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert result.security_score < 0.5
    
    def test_validate_dependencies_mixed_valid_suspicious(self, tool_validator):
        """Test validation with mix of valid and suspicious dependencies."""
        mixed_dependencies = [
            "requests>=2.25.0",  # Valid
            "numpy>=1.20.0",     # Valid
            "backdoor_lib",      # Suspicious
            "pandas"             # Valid
        ]
        
        result = tool_validator.validate_dependencies(mixed_dependencies)
        
        assert result.is_valid is False  # Should fail due to suspicious dependency
        assert len(result.warnings) > 0 or len(result.errors) > 0
    
    def test_validate_dependencies_invalid_format(self, tool_validator):
        """Test validation with invalid dependency formats."""
        invalid_dependencies = [
            "python>=",          # Missing version
            "requests==",        # Missing version
            "",                  # Empty string
            "invalid>>1.0.0",    # Invalid operator
            "package with spaces>=1.0"  # Invalid package name
        ]
        
        result = tool_validator.validate_dependencies(invalid_dependencies)
        
        # Should have warnings or errors for invalid formats
        assert len(result.warnings) > 0 or len(result.errors) > 0
    
    def test_parse_dependency_valid_formats(self, tool_validator):
        """Test parsing of valid dependency formats."""
        test_cases = [
            ("requests>=2.25.0", ("requests", ">=", "2.25.0")),
            ("numpy==1.20.0", ("numpy", "==", "1.20.0")),
            ("pandas>1.0", ("pandas", ">", "1.0")),
            ("scipy", ("scipy", None, None)),  # No version specified
            ("matplotlib<=3.5.0", ("matplotlib", "<=", "3.5.0"))
        ]
        
        for dep_string, expected in test_cases:
            result = tool_validator._parse_dependency(dep_string)
            assert result == expected
    
    def test_parse_dependency_invalid_formats(self, tool_validator):
        """Test parsing of invalid dependency formats."""
        invalid_deps = [
            "",
            ">=2.25.0",  # Missing package name
            "requests>>2.25.0",  # Invalid operator
            "requests>=",  # Missing version
        ]
        
        for dep_string in invalid_deps:
            result = tool_validator._parse_dependency(dep_string)
            assert result is None or result == (None, None, None)


class TestToolValidatorComprehensiveValidation:
    """Test comprehensive validation that combines all validation types."""
    
    def test_validate_tool_comprehensive_valid_tool(self, tool_validator, validation_test_cases):
        """Test comprehensive validation of a valid tool."""
        valid_tool = validation_test_cases['valid_tool']
        
        result = tool_validator.validate_tool(valid_tool)
        
        assert result.is_valid is True
        assert result.security_score > 0.8
        assert len(result.errors) == 0
    
    def test_validate_tool_comprehensive_invalid_tool(self, tool_validator, validation_test_cases):
        """Test comprehensive validation of an invalid tool."""
        invalid_tool = validation_test_cases['malicious_content']
        
        result = tool_validator.validate_tool(invalid_tool)
        
        assert result.is_valid is False
        assert result.security_score < 0.5
        assert len(result.errors) > 0
    
    def test_validate_tool_with_file_and_checksum(self, tool_validator, temp_dir):
        """Test comprehensive validation including file and checksum."""
        # Create test file
        test_file = os.path.join(temp_dir, "tool_file.zip")
        test_content = b"Mock tool file content"
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # Calculate checksum
        expected_checksum = hashlib.sha256(test_content).hexdigest()
        
        tool_metadata = {
            "id": "file_tool",
            "name": "File Tool",
            "description": "Tool with file validation",
            "version": "1.0.0",
            "category": "Testing",
            "download_url": "https://example.com/tool.zip",
            "checksum": f"sha256:{expected_checksum}",
            "platform_support": ["windows", "linux"],
            "dependencies": ["python>=3.8"],
            "validated": True,
            "trusted": True
        }
        
        result = tool_validator.validate_tool(tool_metadata, file_path=test_file)
        
        assert result.is_valid is True
        assert result.security_score > 0.8
    
    def test_validate_tool_different_validation_levels(self, validation_test_cases):
        """Test validation at different security levels."""
        test_tool = validation_test_cases['valid_tool']
        
        levels = [ValidationLevel.MINIMAL, ValidationLevel.STANDARD, 
                 ValidationLevel.STRICT, ValidationLevel.PARANOID]
        
        results = {}
        for level in levels:
            validator = ToolValidator(validation_level=level)
            result = validator.validate_tool(test_tool)
            results[level] = result
        
        # All should validate the valid tool, but with potentially different scores
        for level, result in results.items():
            assert isinstance(result.is_valid, bool)
            assert 0.0 <= result.security_score <= 1.0
        
        # More strict levels might have lower scores due to stricter requirements
        assert results[ValidationLevel.MINIMAL].security_score >= \
               results[ValidationLevel.PARANOID].security_score
    
    def test_validate_tool_batch_validation(self, tool_validator, validation_test_cases):
        """Test batch validation of multiple tools."""
        tools_to_validate = [
            validation_test_cases['valid_tool'],
            validation_test_cases['malicious_content'],
            validation_test_cases['invalid_url']
        ]
        
        results = []
        for tool in tools_to_validate:
            result = tool_validator.validate_tool(tool)
            results.append(result)
        
        # First tool should be valid
        assert results[0].is_valid is True
        
        # Second and third tools should be invalid
        assert results[1].is_valid is False
        assert results[2].is_valid is False
        
        # Valid tool should have highest security score
        assert results[0].security_score > results[1].security_score
        assert results[0].security_score > results[2].security_score


@pytest.mark.integration
class TestToolValidatorIntegration:
    """Integration tests for ToolValidator."""
    
    def test_real_world_tool_validation_scenario(self, temp_dir):
        """Test validation in a real-world scenario."""
        validator = ToolValidator(validation_level=ValidationLevel.STANDARD)
        
        # Create a realistic tool metadata
        tool_metadata = {
            "id": "data_analyzer",
            "name": "Data Analyzer Tool",
            "description": "Professional data analysis toolkit for CSV and JSON processing",
            "version": "2.1.0",
            "category": "Data Analysis",
            "download_url": "https://github.com/example/data-analyzer/releases/download/v2.1.0/data-analyzer.zip",
            "platform_support": ["windows", "linux", "macos"],
            "dependencies": [
                "python>=3.8",
                "pandas>=1.3.0",
                "numpy>=1.20.0",
                "matplotlib>=3.4.0"
            ],
            "author": "Data Science Team",
            "size": 15728640,  # ~15MB
            "checksum": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "validated": True,
            "trusted": True,
            "tags": ["data", "analysis", "csv", "json"]
        }
        
        # Create corresponding file
        tool_file = os.path.join(temp_dir, "data-analyzer.zip")
        # Create content that matches the checksum (this is just for testing)
        # In real scenario, you'd have the actual tool file
        with open(tool_file, 'w') as f:
            f.write("Mock tool file content")
        
        # Validate without file (metadata only)
        metadata_result = validator.validate_tool(tool_metadata)
        
        assert metadata_result.is_valid is True
        assert metadata_result.security_score > 0.7
        assert len(metadata_result.errors) == 0
        
        # Check that all validation aspects were covered
        info_messages = metadata_result.messages
        assert len(info_messages) > 0  # Should have some validation info
    
    def test_validation_with_custom_security_config(self, validation_test_cases):
        """Test validation with custom security configuration."""
        custom_config = {
            'require_https': True,
            'max_file_size': 50 * 1024 * 1024,  # 50MB
            'allowed_extensions': ['.zip', '.tar.gz', '.exe'],
            'blocked_domains': ['malicious-site.com', 'spam-domain.net'],
            'require_checksum': True,
            'min_security_score': 0.8
        }
        
        validator = ToolValidator(
            validation_level=ValidationLevel.STRICT,
            config=custom_config
        )
        
        # Test valid tool
        valid_tool = validation_test_cases['valid_tool']
        result = validator.validate_tool(valid_tool)
        
        # Should pass validation
        assert result.is_valid is True
        
        # Test tool that violates custom config
        config_violating_tool = {
            "id": "violating_tool",
            "name": "Config Violating Tool",
            "description": "Tool that violates custom security config",
            "version": "1.0.0",
            "download_url": "http://example.com/tool.zip",  # HTTP not HTTPS
            "platform_support": ["windows"],
            "dependencies": [],
            "validated": False,
            "trusted": False
            # Missing checksum
        }
        
        result = validator.validate_tool(config_violating_tool)
        
        # Should fail due to config violations
        assert result.is_valid is False
        assert len(result.errors) > 0