# Changelog

## Latest Release

### v0.3.1 (31 July 2025)
- **Complete Localization**: All French text throughout the codebase has been translated to English
- **Important Update Notice Added**: New prominent notice in README about clean reinstall requirement
- Enhanced logging system with improved print capture capabilities
- Better installation tracking with enhanced driver detection

---

## All Releases

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