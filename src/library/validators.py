"""
Tool Validators for Sunshine-AIO Library Integration

This module provides comprehensive validation functionality for tools before installation,
including security validation, schema validation, checksum verification, and platform compatibility checks.
"""

import os
import json
import hashlib
import platform
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Union, Tuple
from enum import Enum
import re
from pathlib import Path

from misc.Logger import log_info, log_error, log_warning, log_success


class ValidationLevel(Enum):
    """Validation strictness levels."""
    MINIMAL = "minimal"         # Basic validation only
    STANDARD = "standard"       # Standard security checks
    STRICT = "strict"          # Enhanced security validation
    PARANOID = "paranoid"      # Maximum security validation


class ValidationResult:
    """
    Result of a validation operation.
    """
    
    def __init__(self, 
                 is_valid: bool = True,
                 level: ValidationLevel = ValidationLevel.STANDARD,
                 messages: List[str] = None,
                 warnings: List[str] = None,
                 errors: List[str] = None,
                 security_score: float = 1.0):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether the validation passed
            level: Validation level used
            messages: General messages
            warnings: Warning messages
            errors: Error messages
            security_score: Security score from 0.0 to 1.0
        """
        self.is_valid = is_valid
        self.level = level
        self.messages = messages or []
        self.warnings = warnings or []
        self.errors = errors or []
        self.security_score = security_score
        self.timestamp = None
        
        # Import datetime here to avoid circular imports
        from datetime import datetime
        self.timestamp = datetime.now()
    
    def add_message(self, message: str, level: str = "info") -> None:
        """Add a message to the appropriate list."""
        if level == "warning":
            self.warnings.append(message)
        elif level == "error":
            self.errors.append(message)
            self.is_valid = False
        else:
            self.messages.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'is_valid': self.is_valid,
            'level': self.level.value,
            'messages': self.messages,
            'warnings': self.warnings,
            'errors': self.errors,
            'security_score': self.security_score,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class ToolValidator:
    """
    Comprehensive tool validation system for security and compatibility checks.
    
    This validator performs multiple types of validation:
    - Schema validation for tool metadata
    - Checksum verification for file integrity
    - Platform compatibility checks
    - Security validation for malicious content
    - Dependency validation
    """
    
    # Tool metadata schema
    TOOL_SCHEMA = {
        "type": "object",
        "required": ["id", "name", "version"],
        "properties": {
            "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
            "name": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": "^[0-9]+\\.[0-9]+\\.[0-9]+"},
            "description": {"type": "string"},
            "author": {"type": "string"},
            "category": {"type": "string"},
            "platform_support": {"type": "array", "items": {"type": "string"}},
            "dependencies": {"type": "array", "items": {"type": "string"}},
            "files": {"type": "array", "items": {"type": "string"}},
            "checksum": {"type": "string"},
            "size": {"type": "integer", "minimum": 0},
            "tags": {"type": "array", "items": {"type": "string"}}
        }
    }
    
    # Dangerous file extensions and patterns
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.so', '.dylib', '.app', '.deb', '.rpm', '.pkg'
    }
    
    SUSPICIOUS_PATTERNS = [
        r'eval\s*\(',              # JavaScript/Python eval
        r'exec\s*\(',              # Python exec
        r'system\s*\(',            # System calls
        r'subprocess\.',           # Python subprocess
        r'os\.system',             # OS system calls
        r'shell_exec',             # PHP shell execution
        r'curl\s+.*\|\s*sh',       # Pipe to shell
        r'wget\s+.*\|\s*sh',       # Pipe to shell
        r'powershell\s+-',         # PowerShell execution
        r'cmd\s*/c',               # Windows command execution
    ]
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the tool validator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = {
            'validation_level': ValidationLevel.STANDARD,
            'max_file_size': 100 * 1024 * 1024,  # 100MB
            'allowed_platforms': ['windows', 'linux', 'macos', 'all'],
            'trusted_authors': [],
            'blocked_patterns': [],
            'checksum_required': True,
            'signature_verification': False,
            'sandbox_validation': False,
            'network_validation': False
        }
        
        if config:
            self.config.update(config)
        
        # Convert validation level string to enum
        if isinstance(self.config['validation_level'], str):
            try:
                self.config['validation_level'] = ValidationLevel(self.config['validation_level'])
            except ValueError:
                self.config['validation_level'] = ValidationLevel.STANDARD
        
        log_info(f"ToolValidator initialized with level: {self.config['validation_level'].value}")
    
    def validate_tool(self, tool_metadata: Dict[str, Any], 
                     tool_files: List[str] = None) -> ValidationResult:
        """
        Perform comprehensive validation of a tool.
        
        Args:
            tool_metadata: Tool metadata dictionary
            tool_files: List of file paths for the tool (optional)
            
        Returns:
            ValidationResult: Comprehensive validation result
        """
        result = ValidationResult(level=self.config['validation_level'])
        
        try:
            log_info(f"Validating tool: {tool_metadata.get('id', 'unknown')}")
            
            # Schema validation
            schema_result = self.validate_schema(tool_metadata)
            if not schema_result.is_valid:
                result.errors.extend(schema_result.errors)
                result.warnings.extend(schema_result.warnings)
                result.is_valid = False
                return result
            
            # Platform compatibility
            platform_result = self.validate_platform_compatibility(tool_metadata)
            result.warnings.extend(platform_result.warnings)
            if not platform_result.is_valid:
                result.errors.extend(platform_result.errors)
                result.is_valid = False
            
            # Security validation
            security_result = self.validate_security(tool_metadata, tool_files)
            result.warnings.extend(security_result.warnings)
            result.security_score = security_result.security_score
            if not security_result.is_valid:
                result.errors.extend(security_result.errors)
                result.is_valid = False
            
            # File validation if files provided
            if tool_files:
                file_result = self.validate_files(tool_files, tool_metadata)
                result.warnings.extend(file_result.warnings)
                if not file_result.is_valid:
                    result.errors.extend(file_result.errors)
                    result.is_valid = False
            
            # Dependency validation
            dependency_result = self.validate_dependencies(tool_metadata)
            result.warnings.extend(dependency_result.warnings)
            if not dependency_result.is_valid:
                result.errors.extend(dependency_result.errors)
                result.is_valid = False
            
            if result.is_valid:
                result.messages.append("Tool validation completed successfully")
                log_success(f"Tool {tool_metadata.get('id')} validation passed")
            else:
                log_warning(f"Tool {tool_metadata.get('id')} validation failed")
            
            return result
            
        except Exception as e:
            result.add_message(f"Validation error: {e}", "error")
            log_error(f"Tool validation error: {e}")
            return result
    
    def validate_schema(self, tool_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate tool metadata against schema.
        
        Args:
            tool_metadata: Tool metadata to validate
            
        Returns:
            ValidationResult: Schema validation result
        """
        result = ValidationResult()
        
        try:
            # Check required fields
            for field in self.TOOL_SCHEMA["required"]:
                if field not in tool_metadata:
                    result.add_message(f"Missing required field: {field}", "error")
            
            # Validate field types and constraints
            self._validate_field_constraints(tool_metadata, result)
            
            # Validate ID format
            tool_id = tool_metadata.get('id', '')
            if tool_id and not re.match(r'^[a-zA-Z0-9_-]+$', tool_id):
                result.add_message(f"Invalid tool ID format: {tool_id}", "error")
            
            # Validate version format
            version = tool_metadata.get('version', '')
            if version and not re.match(r'^[0-9]+\.[0-9]+\.[0-9]+', version):
                result.add_message(f"Invalid version format: {version}", "warning")
            
            # Check for suspicious fields
            suspicious_fields = ['executable', 'command', 'script', 'run']
            for field in suspicious_fields:
                if field in tool_metadata:
                    result.add_message(f"Tool contains potentially dangerous field: {field}", "warning")
            
            if result.is_valid:
                result.messages.append("Schema validation passed")
            
            return result
            
        except Exception as e:
            result.add_message(f"Schema validation error: {e}", "error")
            return result
    
    def _validate_field_constraints(self, metadata: Dict[str, Any], result: ValidationResult) -> None:
        """Validate individual field constraints."""
        
        # Check string fields
        string_fields = ['id', 'name', 'description', 'author', 'category', 'version']
        for field in string_fields:
            value = metadata.get(field)
            if value is not None and not isinstance(value, str):
                result.add_message(f"Field {field} must be a string", "error")
            elif value is not None and len(value.strip()) == 0 and field in ['id', 'name']:
                result.add_message(f"Field {field} cannot be empty", "error")
        
        # Check array fields
        array_fields = ['platform_support', 'dependencies', 'files', 'tags']
        for field in array_fields:
            value = metadata.get(field)
            if value is not None and not isinstance(value, list):
                result.add_message(f"Field {field} must be an array", "error")
        
        # Check numeric fields
        numeric_fields = ['size']
        for field in numeric_fields:
            value = metadata.get(field)
            if value is not None and not isinstance(value, (int, float)):
                result.add_message(f"Field {field} must be numeric", "error")
            elif value is not None and value < 0:
                result.add_message(f"Field {field} cannot be negative", "error")
    
    def validate_platform_compatibility(self, tool_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate platform compatibility.
        
        Args:
            tool_metadata: Tool metadata
            
        Returns:
            ValidationResult: Platform validation result
        """
        result = ValidationResult()
        
        try:
            supported_platforms = tool_metadata.get('platform_support', [])
            
            if not supported_platforms:
                result.add_message("No platform support specified", "warning")
                return result
            
            # Get current platform
            current_platform = platform.system().lower()
            if current_platform == 'windows':
                platform_name = 'windows'
            elif current_platform == 'linux':
                platform_name = 'linux'
            elif current_platform == 'darwin':
                platform_name = 'macos'
            else:
                platform_name = 'unknown'
            
            # Check if current platform is supported
            is_supported = (
                'all' in supported_platforms or
                platform_name in supported_platforms or
                any(p.lower() in supported_platforms for p in [current_platform, platform_name])
            )
            
            if not is_supported:
                result.add_message(
                    f"Tool not compatible with current platform: {platform_name}. "
                    f"Supported: {supported_platforms}",
                    "error"
                )
            else:
                result.messages.append(f"Platform compatibility confirmed: {platform_name}")
            
            # Validate platform names
            valid_platforms = {'windows', 'linux', 'macos', 'all'}
            for platform_entry in supported_platforms:
                if platform_entry.lower() not in valid_platforms:
                    result.add_message(f"Unknown platform: {platform_entry}", "warning")
            
            return result
            
        except Exception as e:
            result.add_message(f"Platform validation error: {e}", "error")
            return result
    
    def validate_security(self, tool_metadata: Dict[str, Any], 
                         tool_files: List[str] = None) -> ValidationResult:
        """
        Perform security validation of the tool.
        
        Args:
            tool_metadata: Tool metadata
            tool_files: Optional list of file paths
            
        Returns:
            ValidationResult: Security validation result
        """
        result = ValidationResult()
        security_score = 1.0
        
        try:
            # Check author trust
            author = tool_metadata.get('author', '').lower()
            if author in [a.lower() for a in self.config.get('trusted_authors', [])]:
                result.messages.append(f"Tool from trusted author: {author}")
                security_score += 0.1
            elif not author or author == 'unknown':
                result.add_message("Tool has unknown or missing author", "warning")
                security_score -= 0.1
            
            # Check for suspicious metadata
            suspicious_keys = ['executable', 'command', 'script', 'run', 'install_command']
            for key in suspicious_keys:
                if key in tool_metadata:
                    result.add_message(f"Tool metadata contains potentially dangerous key: {key}", "warning")
                    security_score -= 0.05
            
            # Check description for suspicious content
            description = tool_metadata.get('description', '').lower()
            suspicious_words = ['hack', 'crack', 'bypass', 'exploit', 'backdoor', 'malware']
            for word in suspicious_words:
                if word in description:
                    result.add_message(f"Tool description contains suspicious word: {word}", "warning")
                    security_score -= 0.1
            
            # Validate file extensions if files provided
            if tool_files:
                dangerous_files = []
                for file_path in tool_files:
                    ext = Path(file_path).suffix.lower()
                    if ext in self.DANGEROUS_EXTENSIONS:
                        dangerous_files.append(file_path)
                        security_score -= 0.2
                
                if dangerous_files:
                    result.add_message(
                        f"Tool contains potentially dangerous files: {dangerous_files}",
                        "warning"
                    )
            
            # Check tool size
            size = tool_metadata.get('size', 0)
            if size > self.config['max_file_size']:
                result.add_message(
                    f"Tool size ({size} bytes) exceeds maximum allowed ({self.config['max_file_size']} bytes)",
                    "error"
                )
                security_score -= 0.3
            
            # Apply validation level adjustments
            if self.config['validation_level'] == ValidationLevel.STRICT:
                security_score -= 0.05  # Be more strict
            elif self.config['validation_level'] == ValidationLevel.PARANOID:
                security_score -= 0.1   # Be very strict
            
            # Ensure security score is within bounds
            security_score = max(0.0, min(1.0, security_score))
            result.security_score = security_score
            
            # Determine if security validation passes
            min_security_score = {
                ValidationLevel.MINIMAL: 0.3,
                ValidationLevel.STANDARD: 0.5,
                ValidationLevel.STRICT: 0.7,
                ValidationLevel.PARANOID: 0.8
            }.get(self.config['validation_level'], 0.5)
            
            if security_score < min_security_score:
                result.add_message(
                    f"Security score {security_score:.2f} below minimum {min_security_score:.2f}",
                    "error"
                )
            else:
                result.messages.append(f"Security validation passed (score: {security_score:.2f})")
            
            return result
            
        except Exception as e:
            result.add_message(f"Security validation error: {e}", "error")
            return result
    
    def validate_files(self, file_paths: List[str], 
                      tool_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate tool files for integrity and security.
        
        Args:
            file_paths: List of file paths to validate
            tool_metadata: Tool metadata for cross-validation
            
        Returns:
            ValidationResult: File validation result
        """
        result = ValidationResult()
        
        try:
            # Check if files exist
            missing_files = []
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)
            
            if missing_files:
                result.add_message(f"Missing files: {missing_files}", "error")
                return result
            
            # Checksum validation
            if self.config['checksum_required']:
                checksum_result = self.validate_checksums(file_paths, tool_metadata)
                result.warnings.extend(checksum_result.warnings)
                if not checksum_result.is_valid:
                    result.errors.extend(checksum_result.errors)
                    result.is_valid = False
            
            # Content scanning
            if self.config['validation_level'] in [ValidationLevel.STRICT, ValidationLevel.PARANOID]:
                content_result = self.scan_file_contents(file_paths)
                result.warnings.extend(content_result.warnings)
                if not content_result.is_valid:
                    result.errors.extend(content_result.errors)
                    result.is_valid = False
            
            return result
            
        except Exception as e:
            result.add_message(f"File validation error: {e}", "error")
            return result
    
    def validate_checksums(self, file_paths: List[str], 
                          tool_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate file checksums against expected values.
        
        Args:
            file_paths: List of file paths
            tool_metadata: Tool metadata containing expected checksums
            
        Returns:
            ValidationResult: Checksum validation result
        """
        result = ValidationResult()
        
        try:
            expected_checksum = tool_metadata.get('checksum')
            
            if not expected_checksum:
                result.add_message("No checksum provided in metadata", "warning")
                return result
            
            # Calculate combined checksum for all files
            hasher = hashlib.sha256()
            for file_path in sorted(file_paths):  # Sort for consistent ordering
                try:
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(8192), b''):
                            hasher.update(chunk)
                except Exception as e:
                    result.add_message(f"Error reading file {file_path}: {e}", "error")
                    return result
            
            calculated_checksum = hasher.hexdigest()
            
            if calculated_checksum != expected_checksum:
                result.add_message(
                    f"Checksum mismatch. Expected: {expected_checksum}, Got: {calculated_checksum}",
                    "error"
                )
            else:
                result.messages.append("Checksum validation passed")
            
            return result
            
        except Exception as e:
            result.add_message(f"Checksum validation error: {e}", "error")
            return result
    
    def scan_file_contents(self, file_paths: List[str]) -> ValidationResult:
        """
        Scan file contents for suspicious patterns.
        
        Args:
            file_paths: List of file paths to scan
            
        Returns:
            ValidationResult: Content scan result
        """
        result = ValidationResult()
        
        try:
            for file_path in file_paths:
                # Skip binary files for content scanning
                if self._is_binary_file(file_path):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Check for suspicious patterns
                    for pattern in self.SUSPICIOUS_PATTERNS:
                        if re.search(pattern, content, re.IGNORECASE):
                            result.add_message(
                                f"Suspicious pattern found in {file_path}: {pattern}",
                                "warning"
                            )
                    
                    # Check for blocked patterns from config
                    for pattern in self.config.get('blocked_patterns', []):
                        if re.search(pattern, content, re.IGNORECASE):
                            result.add_message(
                                f"Blocked pattern found in {file_path}: {pattern}",
                                "error"
                            )
                    
                except Exception as e:
                    result.add_message(f"Error scanning file {file_path}: {e}", "warning")
            
            return result
            
        except Exception as e:
            result.add_message(f"Content scanning error: {e}", "error")
            return result
    
    def _is_binary_file(self, file_path: str) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                return b'\x00' in chunk
        except Exception:
            return True
    
    def validate_dependencies(self, tool_metadata: Dict[str, Any]) -> ValidationResult:
        """
        Validate tool dependencies.
        
        Args:
            tool_metadata: Tool metadata
            
        Returns:
            ValidationResult: Dependencies validation result
        """
        result = ValidationResult()
        
        try:
            dependencies = tool_metadata.get('dependencies', [])
            
            if not dependencies:
                result.messages.append("No dependencies specified")
                return result
            
            # Check dependency format
            for dep in dependencies:
                if not isinstance(dep, str):
                    result.add_message(f"Invalid dependency format: {dep}", "error")
                    continue
                
                # Check if dependency looks like a valid package name
                if not re.match(r'^[a-zA-Z0-9_.-]+$', dep):
                    result.add_message(f"Suspicious dependency name: {dep}", "warning")
            
            # Check for excessive dependencies
            if len(dependencies) > 20:
                result.add_message(
                    f"Tool has excessive dependencies ({len(dependencies)})",
                    "warning"
                )
            
            result.messages.append(f"Dependencies validation completed ({len(dependencies)} deps)")
            return result
            
        except Exception as e:
            result.add_message(f"Dependencies validation error: {e}", "error")
            return result
    
    def quick_validate(self, tool_metadata: Dict[str, Any]) -> bool:
        """
        Perform quick validation for basic tool acceptance.
        
        Args:
            tool_metadata: Tool metadata
            
        Returns:
            bool: True if tool passes quick validation
        """
        try:
            # Check required fields
            required_fields = ['id', 'name', 'version']
            for field in required_fields:
                if field not in tool_metadata:
                    return False
            
            # Check basic format
            tool_id = tool_metadata.get('id', '')
            if not re.match(r'^[a-zA-Z0-9_-]+$', tool_id):
                return False
            
            # Check platform compatibility
            platform_result = self.validate_platform_compatibility(tool_metadata)
            if not platform_result.is_valid:
                return False
            
            return True
            
        except Exception as e:
            log_error(f"Quick validation error: {e}")
            return False
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get current validation configuration."""
        config = self.config.copy()
        config['validation_level'] = config['validation_level'].value
        return config
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update validation configuration.
        
        Args:
            new_config: New configuration values
        """
        self.config.update(new_config)
        
        # Convert validation level string to enum
        if isinstance(self.config['validation_level'], str):
            try:
                self.config['validation_level'] = ValidationLevel(self.config['validation_level'])
            except ValueError:
                self.config['validation_level'] = ValidationLevel.STANDARD
        
        log_info("Validation configuration updated")


def get_tool_validator(config: Dict[str, Any] = None) -> ToolValidator:
    """
    Factory function to get a ToolValidator instance.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ToolValidator: Configured ToolValidator instance
    """
    return ToolValidator(config)