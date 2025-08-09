# Changelog

All notable changes to Sunshine-AIO are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2] - 2025-08-05

### Added
- **Complete Installation Tracking System**
  - Comprehensive tracking of all installed files, registry entries, and services
  - JSON-based installation metadata storage
  - Support for complete component uninstallation
  - Installation verification and integrity checking

- **GUI Interface (In Development)**
  - Graphical interface being developed using CustomTkinter
  - Planned: Real-time installation progress tracking
  - Planned: Component selection with visual feedback
  - Planned: Responsive design with dark/light theme support

- **Enhanced VDD Support**
  - Improved Virtual Display Driver detection logic
  - Better VDD Control integration and automation
  - Support for multiple virtual displays
  - Enhanced driver installation verification

- **Advanced Error Handling**
  - Comprehensive error reporting with context information
  - Graceful failure recovery mechanisms  
  - Detailed logging with multiple severity levels
  - User-friendly error messages with suggested solutions

### Changed
- **Refactored Installation Architecture**
  - Modular component system with clear separation of concerns
  - Improved dependency management between components
  - Better resource cleanup and memory management
  - Enhanced parallel processing capabilities

- **Updated Dependencies**
  - Enhanced requests library with better security
  - Improved psutil for system monitoring
  - Updated colorama for better terminal output
  - CustomTkinter prepared for future GUI interface

- **Enhanced System Integration**
  - Better Windows service management
  - Improved registry handling with backup/restore
  - Enhanced privilege escalation handling
  - More robust system compatibility checks

### Fixed
- **Critical Bug Fixes**
  - Resolved `'DownloadManager' object has no attribute '_tracker'` error
  - Fixed VDD installation hanging on certain system configurations
  - Corrected PowerShell execution policy handling
  - Resolved installation tracking data corruption issues
  - Fixed service installation failures on Windows 11

- **Installation Process Improvements**
  - Fixed race conditions during parallel component installation
  - Resolved path handling issues with spaces and special characters
  - Corrected registry permission problems on restricted systems
  - Fixed cleanup issues when installations are interrupted

### Security
- **Enhanced Security Measures**
  - Improved input validation for all user inputs
  - Better handling of elevated privileges
  - Enhanced download verification with checksums
  - Secure temporary file handling

### Documentation
- **Comprehensive Wiki**
  - Complete user documentation with 10+ guides
  - Technical API reference for developers
  - Architecture overview and design patterns
  - Troubleshooting guide covering all known issues

## [0.3.1] - 2025-07-30

### Added
- **Complete Localization System**
  - Multi-language support framework
  - French translation (100% complete)
  - Dynamic language switching at runtime
  - Extensible system for additional languages

- **Workflow Improvements**
  - Enhanced menu system with better navigation
  - Improved user prompts with clearer instructions
  - Better progress indication during operations
  - Streamlined component selection process

### Changed
- **User Experience Enhancements**
  - More intuitive menu flow and navigation
  - Clearer error messages with actionable solutions
  - Better feedback during long-running operations
  - Improved installation success/failure reporting

- **System Compatibility**
  - Enhanced Sunshine detection logic
  - Better integration with existing installations
  - Improved system requirement validation
  - Enhanced compatibility with Windows 11

### Fixed
- **Localization Issues**
  - Resolved character encoding problems
  - Fixed text overflow in translated menus
  - Corrected language file loading errors
  - Resolved UTF-8 encoding issues in logs

- **Menu System Fixes**
  - Fixed navigation bugs between menu sections
  - Resolved menu state persistence issues
  - Corrected keyboard shortcut handling
  - Fixed menu refresh problems after operations

### Technical
- **Code Quality Improvements**
  - Added comprehensive type hints throughout codebase
  - Improved error handling with specific exception types
  - Enhanced logging with structured output
  - Better code organization and modularity

## [0.3.0] - 2025-07-15

### Added
- **Complete Uninstaller System**
  - Comprehensive component removal capabilities
  - Registry cleanup with backup/restore functionality
  - Service and driver removal with verification
  - File system cleanup with safety checks
  - Rollback support for failed uninstallation attempts

- **Enhanced Component Management**
  - Individual component install/uninstall capability
  - Intelligent dependency management between components
  - Version tracking and compatibility checking
  - Configuration preservation across updates
  - Component health monitoring and verification

- **Advanced System Integration**
  - Robust Windows service lifecycle management
  - Enhanced registry handling with transaction support
  - Improved privilege escalation with UAC integration
  - Better system resource management and cleanup

### Changed
- **Architecture Overhaul**
  - Completely redesigned component installation system
  - Improved separation of concerns between modules
  - Enhanced error propagation and handling
  - Better resource management and cleanup
  - More robust parallel processing capabilities

- **User Interface Improvements**
  - More informative progress indicators with ETA
  - Better error reporting with suggested actions
  - Enhanced logging with multiple output formats
  - Improved installation feedback and confirmation

### Fixed
- **Memory Management**
  - Resolved memory leaks during long installations
  - Fixed resource cleanup issues on process termination
  - Corrected garbage collection problems with large files
  - Improved memory usage during parallel operations

- **Service Management**
  - Fixed service installation failures on restricted systems
  - Resolved service startup issues after installation
  - Corrected service dependency handling
  - Fixed service removal problems during uninstallation

- **System Compatibility**
  - Resolved path handling issues with non-ASCII characters
  - Fixed registry permission problems on enterprise systems
  - Corrected UAC elevation issues on some configurations
  - Resolved compatibility issues with certain antivirus software

### Security
- **Enhanced Security Model**
  - Improved privilege separation and management
  - Better handling of sensitive configuration data
  - Enhanced input validation and sanitization
  - Secure temporary file handling with automatic cleanup

## [0.2.5] - 2025-06-20

### Added
- **Complete Playnite Integration**
  - Automated Playnite installation and configuration
  - Playnite Watcher for enhanced streaming integration
  - Game library metadata management and organization
  - Controller optimization for couch gaming experience
  - Integration with multiple game launchers and platforms

- **Advanced Streaming Optimizations**
  - Enhanced HDR support with automatic detection
  - Improved resolution handling and scaling
  - Better virtual display management and configuration
  - Performance optimizations for various network conditions
  - Adaptive bitrate and quality settings

### Changed
- **Download System Improvements**
  - Faster download speeds with parallel chunk processing
  - Better resume capability for interrupted downloads
  - Enhanced progress reporting with speed and ETA
  - Improved error recovery and retry mechanisms
  - Better bandwidth utilization and throttling

- **Network Error Handling**
  - More robust handling of network timeouts
  - Better recovery from intermittent connection issues
  - Enhanced proxy and firewall compatibility
  - Improved download verification and integrity checking

### Fixed
- **Installation Reliability**
  - Fixed component installation order dependencies
  - Resolved race conditions in parallel installations
  - Corrected cleanup issues on installation failure
  - Fixed progress reporting accuracy issues

## [0.2.0] - 2025-05-15

### Added
- **Virtual Display Driver Support**
  - Complete IDD Sample Driver integration
  - Multi-virtual display support with custom configurations
  - Custom resolution and refresh rate configuration
  - HDR passthrough capability for compatible displays
  - Automatic virtual display management

- **Sunshine Virtual Monitor System**
  - Advanced display management with PowerShell scripts
  - Dynamic resolution matching based on client capabilities
  - Multi-monitor configuration support and management
  - VSync control integration for better performance
  - Automated display profile switching

- **Enhanced Component System**
  - Modular installation architecture with dependency tracking
  - Better component isolation and error handling
  - Individual component enable/disable functionality
  - Component health monitoring and automatic recovery

### Changed
- **System Architecture**
  - Redesigned installation system for better modularity
  - Improved error handling and recovery mechanisms
  - Better separation between core and optional components
  - Enhanced system compatibility checking

- **Performance Improvements**
  - Faster installation process with parallel operations
  - Better memory usage during component downloads
  - Improved startup time and responsiveness
  - Enhanced system resource management

### Fixed
- **Stability Issues**
  - Resolved crashes during component installation
  - Fixed memory leaks in download manager
  - Corrected race conditions in parallel operations
  - Improved error recovery and graceful degradation

## [0.1.0] - 2025-04-01

### Added
- **Initial Release Features**
  - Basic Sunshine streaming server installation
  - Automated configuration and setup
  - Windows service integration and management
  - Simple command-line interface
  - Basic system requirements checking

- **Core Installation System**
  - Download management with progress tracking
  - Basic error handling and user feedback
  - Installation verification and health checking
  - System compatibility validation

- **Foundation Features**
  - Modular design for future component additions
  - Basic logging and diagnostic capabilities
  - Windows service lifecycle management
  - Configuration file management

### Technical Details
- **Initial Architecture**
  - Python-based installation system
  - Windows-focused implementation
  - Basic component management framework
  - Simple CLI interface for user interaction

## [Unreleased]

### Planned for 0.4.0
- **Web-based Management Interface**
  - Modern web UI for remote management
  - Real-time monitoring and configuration
  - Mobile-responsive design for tablet/phone access
  - API endpoints for third-party integration

- **Cloud Configuration Sync**
  - Backup and restore configurations to cloud storage
  - Multi-device configuration synchronization
  - Version control for configuration changes
  - Disaster recovery capabilities

- **Advanced HDR Management**
  - Automatic HDR detection and configuration
  - Game-specific HDR profiles and optimization
  - HDR calibration tools and testing utilities
  - Advanced tone mapping and color management

### Planned for 0.5.0
- **Enterprise Features**
  - Multi-user support with role-based access
  - Centralized deployment and management tools
  - Advanced monitoring and analytics
  - Integration with enterprise identity systems

- **Performance Enhancements**
  - GPU-accelerated processing where possible
  - Advanced caching and optimization
  - Network optimization and QoS integration
  - Performance monitoring and alerting

---

## Version Support Policy

| Version | Release Date | Support Status | End of Support |
|---------|--------------|----------------|----------------|
| 0.3.2   | 2025-08-05  | ✅ Active      | TBD            |
| 0.3.1   | 2025-07-30  | ⚠️ Security Only | 2025-11-01   |
| 0.3.0   | 2025-07-15  | ❌ End of Life | 2025-08-15    |
| 0.2.x   | 2025-05-15  | ❌ End of Life | 2025-07-15    |
| 0.1.x   | 2025-04-01  | ❌ End of Life | 2025-05-15    |

## Migration Notes

- **0.3.1 → 0.3.2**: Automatic migration with configuration preservation
- **0.3.0 → 0.3.2**: Recommended clean installation due to architecture changes  
- **0.2.x → 0.3.x**: Clean installation required, manual configuration migration
- **0.1.x → Current**: Complete reinstallation required

For detailed migration instructions, see the [Migration Guide](Migration-Guide).

---

*This changelog follows [Keep a Changelog](https://keepachangelog.com/) format. For the most up-to-date release information, check our [GitHub Releases](https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases) page.*