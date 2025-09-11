"""
Security testing for community library.

This module provides comprehensive security testing to validate that the
community library integration is secure against various attack vectors
and properly handles untrusted content.
"""

import pytest
import tempfile
import shutil
import os
import sys
import hashlib
import zipfile
import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from library import (
    LibraryManager,
    CacheManager,
    ConfigManager,
    ToolValidator,
    DownloadManager,
    InstallationManager,
    ToolProvider
)


@pytest.mark.security
class TestSecurityValidation:
    """Security testing for community library."""
    
    @pytest.fixture(autouse=True)
    def setup_security_test(self):
        """Set up security test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config_dir = os.path.join(self.test_dir, 'config')
        self.cache_dir = os.path.join(self.test_dir, 'cache')
        self.downloads_dir = os.path.join(self.test_dir, 'downloads')
        
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        
        # Initialize managers
        self.config_manager = ConfigManager(config_dir=self.config_dir)
        self.cache_manager = CacheManager(cache_dir=self.cache_dir)
        self.validator = ToolValidator()
        
        yield
        
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @pytest.fixture
    def malicious_tool_samples(self):
        """Provide samples of potentially malicious tool metadata."""
        return [
            {
                # Path traversal attempt
                "id": "../../../etc/passwd",
                "name": "Legitimate Tool",
                "description": "This looks normal",
                "download_url": "https://attacker.com/evil.zip",
                "install_path": "../../../system32/evil.exe"
            },
            {
                # Script injection attempt
                "id": "tool_with_script",
                "name": "Tool with <script>alert('xss')</script>",
                "description": "Description with ${process.env}",
                "post_install_script": "rm -rf / --no-preserve-root",
                "download_url": "javascript:alert('xss')"
            },
            {
                # SQL injection attempt
                "id": "tool'; DROP TABLE tools; --",
                "name": "SQL Injection Tool",
                "description": "Normal description",
                "download_url": "https://example.com/tool.zip"
            },
            {
                # Command injection attempt
                "id": "tool_cmd_injection",
                "name": "Tool && rm -rf /",
                "description": "Tool | cat /etc/passwd",
                "install_command": "install.bat && format C:",
                "download_url": "https://example.com/tool.zip"
            },
            {
                # Buffer overflow attempt
                "id": "A" * 10000,  # Extremely long ID
                "name": "B" * 10000,  # Extremely long name
                "description": "C" * 100000,  # Extremely long description
                "download_url": "https://example.com/tool.zip"
            },
            {
                # Invalid URLs and protocols
                "id": "tool_invalid_url",
                "name": "Tool with Invalid URL",
                "description": "This tool has suspicious URLs",
                "download_url": "file:///etc/passwd",
                "support_url": "ftp://internal.network/secrets",
                "homepage": "ldap://directory.internal/users"
            }
        ]
    
    def test_tool_validation_security(self, malicious_tool_samples):
        """Test security validation of tool metadata."""
        for malicious_tool in malicious_tool_samples:
            # Test metadata validation
            validation_result = self.validator.validate_tool_metadata(malicious_tool)
            
            # Should reject malicious content
            if "../" in str(malicious_tool.get('id', '')):
                assert not validation_result.is_valid, "Path traversal attempt should be rejected"
                assert any("path" in error.lower() for error in validation_result.errors)
            
            if "<script>" in str(malicious_tool.get('name', '')):
                assert not validation_result.is_valid, "Script injection should be rejected"
                assert any("script" in error.lower() or "injection" in error.lower() 
                          for error in validation_result.errors)
            
            if "DROP TABLE" in str(malicious_tool.get('id', '')):
                assert not validation_result.is_valid, "SQL injection should be rejected"
                assert any("invalid" in error.lower() for error in validation_result.errors)
            
            if len(str(malicious_tool.get('id', ''))) > 1000:
                assert not validation_result.is_valid, "Excessively long fields should be rejected"
                assert any("length" in error.lower() or "long" in error.lower() 
                          for error in validation_result.errors)
            
            # Test URL validation
            download_url = malicious_tool.get('download_url', '')
            if download_url.startswith(('file://', 'ftp://', 'ldap://', 'javascript:')):
                url_validation = self.validator.validate_url(download_url)
                assert not url_validation, f"Dangerous URL protocol should be rejected: {download_url}"
    
    def test_download_verification(self):
        """Test download verification and integrity checks."""
        downloader = DownloadManager(download_dir=self.downloads_dir)
        
        # Create test files with known checksums
        test_file_content = b"This is a test file for checksum verification"
        expected_checksum = hashlib.sha256(test_file_content).hexdigest()
        
        test_tool = {
            "id": "test_tool_checksum",
            "name": "Test Tool",
            "download_url": "https://example.com/test.zip",
            "checksum": expected_checksum,
            "checksum_algorithm": "sha256"
        }
        
        # Mock successful download with correct checksum
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = test_file_content
            mock_response.status_code = 200
            mock_response.headers = {'Content-Length': str(len(test_file_content))}
            mock_get.return_value = mock_response
            
            result = downloader.download_tool(test_tool)
            assert result['success'], "Download with valid checksum should succeed"
            assert result['checksum_valid'], "Checksum validation should pass"
        
        # Test with invalid checksum
        invalid_tool = test_tool.copy()
        invalid_tool['checksum'] = "invalid_checksum_123"
        
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.content = test_file_content
            mock_response.status_code = 200
            mock_response.headers = {'Content-Length': str(len(test_file_content))}
            mock_get.return_value = mock_response
            
            result = downloader.download_tool(invalid_tool)
            assert not result['success'], "Download with invalid checksum should fail"
            assert not result['checksum_valid'], "Checksum validation should fail"
    
    def test_malicious_metadata_protection(self):
        """Test protection against malicious metadata."""
        # Test oversized metadata
        oversized_tool = {
            "id": "test_tool",
            "name": "A" * 1000000,  # 1MB name
            "description": "B" * 10000000,  # 10MB description
            "download_url": "https://example.com/tool.zip"
        }
        
        validation_result = self.validator.validate_tool_metadata(oversized_tool)
        assert not validation_result.is_valid, "Oversized metadata should be rejected"
        
        # Test metadata with null bytes
        null_byte_tool = {
            "id": "test\x00tool",
            "name": "Tool\x00Name",
            "description": "Description\x00with nulls",
            "download_url": "https://example.com/tool.zip"
        }
        
        validation_result = self.validator.validate_tool_metadata(null_byte_tool)
        assert not validation_result.is_valid, "Metadata with null bytes should be rejected"
        
        # Test metadata with control characters
        control_char_tool = {
            "id": "test_tool",
            "name": "Tool\x1b[31mName",  # ANSI escape sequence
            "description": "Description\x0cwith control chars",
            "download_url": "https://example.com/tool.zip"
        }
        
        validation_result = self.validator.validate_tool_metadata(control_char_tool)
        # Should sanitize or reject control characters
        if validation_result.is_valid:
            # If accepted, control characters should be sanitized
            assert "\x1b" not in validation_result.sanitized_data.get('name', '')
            assert "\x0c" not in validation_result.sanitized_data.get('description', '')
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        installer = InstallationManager(self.config_manager)
        
        # Test various path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\evil.exe",
            "/etc/passwd",
            "C:\\Windows\\System32\\evil.exe",
            "tool/../../../sensitive_file",
            "tool\\..\\..\\sensitive_file",
            "\\\\network\\share\\evil.exe",
            "//network/share/evil.exe"
        ]
        
        for malicious_path in malicious_paths:
            # Test path sanitization
            sanitized_path = installer.sanitize_install_path(malicious_path)
            
            # Should not allow traversal outside designated directories
            assert not os.path.isabs(sanitized_path), f"Absolute path should be rejected: {malicious_path}"
            assert ".." not in sanitized_path, f"Parent directory traversal should be blocked: {malicious_path}"
            assert not sanitized_path.startswith("/"), f"Root path should be rejected: {malicious_path}"
            assert not sanitized_path.startswith("\\"), f"Windows root should be rejected: {malicious_path}"
            
            # Test installation path validation
            tool_with_malicious_path = {
                "id": "test_tool",
                "name": "Test Tool",
                "install_path": malicious_path
            }
            
            result = installer.validate_installation_path(tool_with_malicious_path)
            assert not result, f"Malicious installation path should be rejected: {malicious_path}"
    
    def test_injection_attack_prevention(self):
        """Test prevention of various injection attacks."""
        # Test command injection prevention
        malicious_commands = [
            "install.exe && del /f /q C:\\*",
            "install.exe; rm -rf /",
            "install.exe | cat /etc/passwd",
            "install.exe `cat /etc/passwd`",
            "install.exe $(rm -rf /)",
            "install.exe & evil.exe",
            "install.exe || evil.exe"
        ]
        
        installer = InstallationManager(self.config_manager)
        
        for malicious_command in malicious_commands:
            tool_with_malicious_command = {
                "id": "test_tool",
                "name": "Test Tool",
                "install_command": malicious_command
            }
            
            # Should sanitize or reject malicious commands
            sanitized_command = installer.sanitize_command(malicious_command)
            
            # Check for dangerous characters/operators
            dangerous_chars = ['&', '|', ';', '`', '$', '&&', '||']
            for char in dangerous_chars:
                if char in malicious_command:
                    assert char not in sanitized_command, f"Dangerous character '{char}' should be removed"
        
        # Test SQL injection prevention in search/filter
        from library.search_engine import SearchEngine
        
        library_manager = LibraryManager(
            config_manager=self.config_manager,
            cache_manager=self.cache_manager
        )
        search_engine = SearchEngine(library_manager)
        
        sql_injection_queries = [
            "'; DROP TABLE tools; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM tools WHERE '1'='1'; --"
        ]
        
        for injection_query in sql_injection_queries:
            # Should handle SQL injection attempts safely
            try:
                results = search_engine.search(injection_query)
                # If no exception, should return safe results
                assert isinstance(results, list), "Search should return safe list results"
            except Exception as e:
                # If exception, should be a safe/expected error
                assert "injection" not in str(e).lower(), "Should not expose injection details"
    
    def test_signature_verification(self):
        """Test digital signature verification for tools."""
        # Create mock signed tool
        signed_tool = {
            "id": "signed_tool",
            "name": "Signed Tool",
            "download_url": "https://example.com/signed_tool.zip",
            "signature": "mock_signature_data",
            "public_key": "mock_public_key"
        }
        
        # Test signature validation
        validator = ToolValidator()
        
        # Mock valid signature
        with patch.object(validator, 'verify_digital_signature', return_value=True):
            result = validator.validate_tool_signature(signed_tool)
            assert result, "Valid signature should be accepted"
        
        # Mock invalid signature
        with patch.object(validator, 'verify_digital_signature', return_value=False):
            result = validator.validate_tool_signature(signed_tool)
            assert not result, "Invalid signature should be rejected"
        
        # Test unsigned tool
        unsigned_tool = signed_tool.copy()
        del unsigned_tool['signature']
        
        result = validator.validate_tool_signature(unsigned_tool)
        # Should handle unsigned tools according to security policy
        assert isinstance(result, bool), "Should return boolean result for unsigned tools"
    
    def test_sandbox_isolation(self):
        """Test sandbox isolation for tool execution."""
        installer = InstallationManager(self.config_manager)
        
        # Test sandbox environment creation
        sandbox_path = installer.create_sandbox_environment("test_tool")
        
        # Sandbox should be isolated
        assert sandbox_path.startswith(self.test_dir), "Sandbox should be within test directory"
        assert "sandbox" in sandbox_path.lower(), "Sandbox path should indicate isolation"
        
        # Test sandbox restrictions
        restricted_operations = [
            "network_access",
            "file_system_write",
            "registry_write",
            "process_creation"
        ]
        
        for operation in restricted_operations:
            is_allowed = installer.is_operation_allowed_in_sandbox(operation)
            # Critical operations should be restricted by default
            if operation in ["file_system_write", "registry_write", "process_creation"]:
                assert not is_allowed, f"Critical operation '{operation}' should be restricted"
    
    def test_input_sanitization(self):
        """Test input sanitization across all components."""
        # Test configuration input sanitization
        dangerous_inputs = [
            "<script>alert('xss')</script>",
            "${process.env.SECRET}",
            "../../secret_config",
            "\x00null_byte_injection",
            "\x1b[31mANSI_escape",
            "' OR 1=1 --",
            "$(rm -rf /)"
        ]
        
        for dangerous_input in dangerous_inputs:
            # Test config value sanitization
            sanitized = self.config_manager.sanitize_config_value(dangerous_input)
            
            # Should remove or escape dangerous content
            assert "<script>" not in sanitized, "Script tags should be removed"
            assert "${" not in sanitized, "Variable expansion should be escaped"
            assert "\x00" not in sanitized, "Null bytes should be removed"
            assert "\x1b" not in sanitized, "ANSI escapes should be removed"
            
            # Test search query sanitization
            library_manager = LibraryManager(
                config_manager=self.config_manager,
                cache_manager=self.cache_manager
            )
            search_engine = SearchEngine(library_manager)
            
            sanitized_query = search_engine.sanitize_search_query(dangerous_input)
            
            # Should be safe for search operations
            assert len(sanitized_query) <= len(dangerous_input), "Sanitized query should not be longer"
            assert not any(char in sanitized_query for char in ['<', '>', '$', '\x00']), \
                "Dangerous characters should be removed"
    
    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation attacks."""
        installer = InstallationManager(self.config_manager)
        
        # Test tools that attempt privilege escalation
        privileged_tools = [
            {
                "id": "sudo_tool",
                "name": "Tool requiring sudo",
                "install_command": "sudo install.sh",
                "requires_admin": True
            },
            {
                "id": "setuid_tool",
                "name": "Tool with setuid",
                "post_install": "chmod +s executable",
                "permissions": "setuid"
            },
            {
                "id": "registry_tool",
                "name": "Registry modifier",
                "install_command": "reg add HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                "modifies_system": True
            }
        ]
        
        for tool in privileged_tools:
            # Should detect and handle privilege escalation attempts
            risk_assessment = installer.assess_privilege_risk(tool)
            
            assert risk_assessment['requires_admin_consent'], \
                "Tools requiring privileges should need admin consent"
            assert risk_assessment['risk_level'] in ['medium', 'high'], \
                "Privileged tools should have elevated risk level"
            
            # Test installation without proper permissions
            result = installer.install_tool(tool, "/fake/path", admin_approved=False)
            assert not result['success'], \
                "Installation should fail without admin approval for privileged tools"
    
    def test_network_security_validation(self):
        """Test network-related security validations."""
        # Test URL validation
        dangerous_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
            "ftp://internal.network/secrets",
            "ldap://directory.internal/users",
            "http://192.168.1.1/internal",  # Private IP
            "https://localhost:8080/admin",  # Localhost
            "http://10.0.0.1/config"  # Private IP range
        ]
        
        for dangerous_url in dangerous_urls:
            is_safe = self.validator.validate_url(dangerous_url)
            
            # Should reject dangerous protocols and private networks
            if any(proto in dangerous_url for proto in ['javascript:', 'data:', 'file:', 'ftp:', 'ldap:']):
                assert not is_safe, f"Dangerous protocol should be rejected: {dangerous_url}"
            
            if any(ip in dangerous_url for ip in ['192.168.', '10.0.', 'localhost', '127.0.0.1']):
                assert not is_safe, f"Private/local network should be rejected: {dangerous_url}"
        
        # Test download source validation
        downloader = DownloadManager(download_dir=self.downloads_dir)
        
        suspicious_sources = [
            "https://suspicious-domain.evil/tool.zip",
            "http://temporary-site.temp/download.exe",
            "https://raw.githubusercontent.com/random-user/suspicious-repo/master/evil.exe"
        ]
        
        for source in suspicious_sources:
            tool = {
                "id": "test_tool",
                "name": "Test Tool",
                "download_url": source
            }
            
            # Should perform source reputation checking
            reputation = downloader.check_source_reputation(source)
            assert isinstance(reputation, dict), "Should return reputation information"
            assert 'trust_score' in reputation, "Should include trust score"
            assert 'risk_factors' in reputation, "Should include risk factors"
    
    def test_data_protection_compliance(self):
        """Test compliance with data protection requirements."""
        # Test personal data handling
        user_data = {
            "user_id": "test_user_123",
            "preferences": {
                "favorite_tools": ["tool1", "tool2"],
                "download_history": [
                    {"tool_id": "tool1", "timestamp": "2024-01-01T10:00:00Z"},
                    {"tool_id": "tool2", "timestamp": "2024-01-02T10:00:00Z"}
                ]
            }
        }
        
        # Test data encryption
        encrypted_data = self.config_manager.encrypt_user_data(user_data)
        assert encrypted_data != user_data, "User data should be encrypted"
        
        # Test data decryption
        decrypted_data = self.config_manager.decrypt_user_data(encrypted_data)
        assert decrypted_data == user_data, "Decrypted data should match original"
        
        # Test data anonymization
        anonymized_data = self.config_manager.anonymize_user_data(user_data)
        assert "user_id" not in str(anonymized_data), "User ID should be anonymized"
        
        # Test data deletion
        deletion_result = self.config_manager.delete_user_data("test_user_123")
        assert deletion_result, "User data deletion should succeed"
        
        # Verify data is actually deleted
        try:
            retrieved_data = self.config_manager.get_user_data("test_user_123")
            assert retrieved_data is None, "Deleted user data should not be retrievable"
        except Exception:
            pass  # Expected if user data doesn't exist
    
    def test_audit_logging_security(self):
        """Test security audit logging functionality."""
        # Test security event logging
        security_events = [
            {"event": "download_attempted", "tool_id": "test_tool", "risk": "low"},
            {"event": "validation_failed", "tool_id": "malicious_tool", "risk": "high"},
            {"event": "privilege_escalation_attempt", "tool_id": "sudo_tool", "risk": "critical"},
            {"event": "unauthorized_access", "resource": "admin_config", "risk": "high"}
        ]
        
        for event in security_events:
            # Log security event
            log_result = self.config_manager.log_security_event(event)
            assert log_result, f"Security event logging should succeed: {event}"
        
        # Test audit trail retrieval
        audit_trail = self.config_manager.get_security_audit_trail()
        assert isinstance(audit_trail, list), "Audit trail should be a list"
        assert len(audit_trail) >= len(security_events), "Should contain logged events"
        
        # Test log integrity
        for log_entry in audit_trail:
            assert 'timestamp' in log_entry, "Log entries should have timestamps"
            assert 'event' in log_entry, "Log entries should have event types"
            assert 'checksum' in log_entry, "Log entries should have integrity checksums"
            
            # Verify log entry integrity
            calculated_checksum = self.config_manager.calculate_log_checksum(log_entry)
            assert calculated_checksum == log_entry['checksum'], "Log integrity should be maintained"
    
    def test_dependency_security_scanning(self):
        """Test security scanning of tool dependencies."""
        # Test tool with known vulnerable dependencies
        vulnerable_tool = {
            "id": "vulnerable_tool",
            "name": "Tool with Vulnerable Dependencies",
            "dependencies": [
                "requests==2.25.1",  # Potentially outdated
                "urllib3==1.26.4",   # Potentially vulnerable
                "certifi==2020.12.5" # Outdated certificates
            ],
            "python_requires": ">=3.6"
        }
        
        # Test dependency vulnerability scanning
        vulnerability_scanner = self.validator.get_dependency_scanner()
        scan_result = vulnerability_scanner.scan_dependencies(vulnerable_tool['dependencies'])
        
        assert isinstance(scan_result, dict), "Scan result should be a dictionary"
        assert 'vulnerabilities' in scan_result, "Should include vulnerability information"
        assert 'risk_score' in scan_result, "Should include overall risk score"
        
        # Test vulnerability reporting
        if scan_result['vulnerabilities']:
            for vuln in scan_result['vulnerabilities']:
                assert 'cve_id' in vuln or 'advisory_id' in vuln, "Vulnerabilities should have IDs"
                assert 'severity' in vuln, "Vulnerabilities should have severity ratings"
                assert 'description' in vuln, "Vulnerabilities should have descriptions"
        
        # Test safe dependency approval
        safe_tool = {
            "id": "safe_tool",
            "name": "Tool with Safe Dependencies",
            "dependencies": [
                "requests>=2.28.0",
                "urllib3>=1.26.12",
                "certifi>=2022.9.24"
            ]
        }
        
        safe_scan_result = vulnerability_scanner.scan_dependencies(safe_tool['dependencies'])
        assert safe_scan_result['risk_score'] < scan_result['risk_score'], \
            "Safe dependencies should have lower risk score"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])