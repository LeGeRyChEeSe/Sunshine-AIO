# Changelog

## v0.3.0 (31 July 2025)

### Added
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

### Changed
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

### Fixed
- Menu display truncation issues - logo now shows complete application name
- Uninstallation system now handles custom installation paths properly
- Better error handling and user feedback during operations
- Improved compatibility with different Windows configurations