# Changelog

## Latest Release

### v0.3.7 (1 October 2025)
- **Enhanced GitHub Release Download**: Improved download reliability with fallback pattern matching for changing release naming conventions (resolves #39)
- **Better Error Handling**: Added detailed logging when download patterns don't match release assets
- **Improved User Experience**: Added pause after action execution for better menu readability

---

## All Releases

### v0.3.7 (1 October 2025)

#### Fixed
- **GitHub Download Fallback Patterns**: Enhanced download system to handle changing release asset naming conventions (resolves #39)
  - Added fallback pattern matching for components like Sunshine installer
  - Improved error messages with detailed information when patterns don't match
  - Better logging to help diagnose download issues

#### Changed
- **Menu User Experience**: Added pause after executing menu actions to allow users to read output messages
  - Navigation functions (next/previous page, back to main) skip the pause for smoother navigation
  - Improves readability and prevents important messages from disappearing

#### Enhanced
- **Download Manager Validation**: Added download URL validation before making requests
- **Error Reporting**: More informative error messages including GitHub URL and attempted patterns

### v0.3.6 (14 September 2025)

### v0.3.6 (14 September 2025)

#### Fixed
- **Path Resolution Issue**: Enhanced path handling in main.py by using absolute paths (`os.path.abspath()`) to prevent relative path issues
- **Installer Script Robustness**: Resolved issue #28 where path resolution could fail in certain environments

#### Changed
- **Gitignore Updates**: Added comprehensive patterns to prevent tracking of:
  - Build artifacts (`*.egg-info/`, `build/`, `dist/`)
  - Cache directories (`cache/`, `src/cache/`, `.pytest_cache/`)
  - User data directories (`src/user_data/`)
  - Backup and library directories (`src/backups/`, `src/library/`)

### v0.3.5 (27 August 2025)

#### Fixed
- **SyntaxError Resolution**: Fixed invalid f-string expression with backslashes in `Uninstaller.py:771`
- **PowerShell Command Generation**: Updated VDD device detection to use static pattern matching instead of dynamic f-string interpolation
- **Python Version Compatibility**: Ensured application works correctly on Python 3.10.11 and 3.11.9

### v0.3.3 (10 August 2025)

#### Added
- **High-Quality Application Icons**: New sunshine-aio.png and sunshine-aio.ico with improved visual quality
- **Enhanced Visual Branding**: Professional-grade icons with multiple size support (16x16 to 512x512)

#### Changed
- **Updated Icon References**: All codebase references now point to new icon files
- **Improved README Display**: Logo updated to use high-quality PNG format
- **Compiler Configuration**: Build process updated to use new icon assets

#### Removed
- **Legacy Icon Files**: Removed outdated sunshine_aio.ico and sunshine_aio.jpg files

### v0.3.2 (1 August 2025)

#### Added
- **Automatic Sunshine Installation Detection**: New intelligent detection system that finds Sunshine installations via:
  - Windows Registry scanning for official installation entries
  - Common installation paths checking (Program Files, AppData, etc.)
  - PATH environment variable analysis
  - Real-time installation tracker updates with detected paths
- **Enhanced VDD Driver Support**: Comprehensive Virtual Display Driver management:
  - Support for both legacy (IddSampleDriver) and modern (MttVDD) drivers
  - Automatic driver type detection using Windows driver store analysis
  - Improved driver installation tracking and removal capabilities
  - Better compatibility with different VDD versions
- **Smart Installation Discovery**: Automatic scanning and registration of existing tools:
  - Comprehensive tools directory scanning for installed components
  - Auto-detection of Sunshine Virtual Monitor, VDD Control, and other tools
  - Intelligent mapping of directory names to component types
  - Automatic installation tracker updates for discovered components

#### Enhanced
- **Complete Uninstallation Process**: Improved full removal capabilities:
  - Complete tools directory cleanup during full uninstallation
  - Enhanced file and directory removal with better error handling
  - Improved cleanup verification and reporting
- **Installation Tracker System**: Enhanced tracking capabilities:
  - New `force_update_detected_path()` method for manual path updates
  - Better handling of auto-detected vs manually installed components
  - Improved installation metadata storage and retrieval
- **User Interface Improvements**: Better component status display:
  - Enhanced installed components view with automatic detection
  - Improved component discovery feedback and logging
  - Better error handling and user feedback during detection

#### Technical Improvements
- Better error handling for installation path detection edge cases
- Enhanced logging for installation detection and tracking processes
- Improved code organization and method separation for detection logic
- Enhanced Windows registry interaction with better error handling

### v0.3.1 (31 July 2025)

#### Changed
- **Complete Localization**: All French text throughout the codebase has been translated to English
  - User interface messages, menus, and prompts are now fully in English
  - Docstrings, code comments, and technical documentation translated
  - Log messages and error notifications converted to English
  - Maintains all original functionality while ensuring complete English localization
- **Important Update Notice Added**: New prominent notice in README about clean reinstall requirement
  - Clear instructions for users upgrading from previous versions
  - Information about new shortcut-based launcher system
  - Notification that future updates will be automatic (one-time manual process)

#### Technical Improvements
- Enhanced logging system with improved print capture capabilities
- Better installation tracking with enhanced driver detection
- Improved system analysis and component detection

### v0.3.0 (31 July 2025)

#### Added
- **Intelligent Uninstallation System**: Complete system overhaul for comprehensive tool removal
  - New `InstallationTracker` module that tracks all installation details (paths, services, drivers, registry entries)
  - Custom installation paths are now remembered for proper uninstallation
  - **Smart Official Uninstaller Detection**: Automatically searches and prioritizes official uninstallers
    - Searches in installation directories for standard uninstaller files
    - Scans Windows registry for registered uninstall commands
    - Supports multiple formats: .exe, .bat, .ps1 scripts
    - Tests various silent installation arguments automatically
  - **Fallback Manual Removal**: Only performs manual cleanup when official uninstallers fail or aren't found
  - Advanced driver removal for Virtual Display Driver using `pnputil`
  - Registry cleanup for all installed tools
  - Windows Firewall rules cleanup for Sunshine
  - Service removal and cleanup
  - Post-uninstallation verification to ensure complete removal

#### Changed
- **Enhanced Installation Tracking**: All installation functions now register their details
  - Sunshine installation paths and services are tracked
  - Virtual Display Driver installation and driver details are recorded
  - Sunshine Virtual Monitor and dependencies (MMT, VSync Toggle) are tracked
  - Playnite and Playnite Watcher installations are monitored
  - Custom installation directories chosen by users are remembered
- **Improved Menu Display**: 
  - Fixed logo display to show complete "Sunshine-AIO" ASCII art
  - Better alignment and centering of all UI elements
  - Logo now loads from external file `src/misc/ressources/logo_menu.txt`
  - Restored original interface style with Unicode box characters
- **Enhanced Logging**: More detailed logging throughout installation and uninstallation processes

#### Fixed
- Menu display truncation issues - logo now shows complete application name
- Uninstallation system now handles custom installation paths properly
- Better error handling and user feedback during operations
- Improved compatibility with different Windows configurations

### v0.2.1 (2024)

#### Fixed
- **Path with Spaces Issue**: Implemented workaround for installations in directories containing spaces ([#17](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/17))
- **Virtual Display Driver Issues**: Fixed download and installation problems ([#23](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/23))
- Documentation improvements and README updates

### v0.2.0-dev (2024)

#### Added
- **Auto-Resolution Feature**: Automatic resolution detection and configuration
- **Performance Optimizations**: Various improvements to installation process
- Enhanced user experience with better prompts and feedback

#### Changed
- Major code optimizations and refactoring
- Improved error handling throughout the application

### v0.1.1-dev (2024)

#### Added
- **Security Notice**: Added warning about false positive antivirus detections
- Initial development release with basic functionality

#### Fixed
- Virtual Display Driver issues at Windows startup
- Sunshine Virtual Monitor installation problems
- Playnite Watcher functionality improvements

#### Technical
- Code rework and structure improvements
- Repository setup and development workflow enhancements