# Release Notes

## 🚀 Version 0.3.2 - Enhanced Installation Detection and VDD Support

**Release Date:** August 5, 2025  
**Download:** [GitHub Releases](https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases/tag/v0.3.2)

### ⚡ Quick Update
```powershell
# Fastest way to update (Run as Administrator)
irm https://sunshine-aio.com/script.ps1 | iex
# When prompted, provide your existing installation path for automatic update
```

### ✨ New Features

#### Installation Tracking System
- **Complete installation tracker** for all components
- **Tracks files, registry entries, services, and drivers**
- **Enables complete uninstallation** of all components
- **Installation metadata** stored in `installation_tracker.json`

#### Enhanced VDD Support
- **Improved Virtual Display Driver detection**
- **Better VDD Control integration**
- **Enhanced driver installation verification**
- **Support for multiple virtual displays**

#### GUI Interface (In Development)
- **Graphical interface in development** using CustomTkinter
- **Planned features:** Real-time installation progress tracking
- **Modern, user-friendly design** being implemented
- **Component selection with visual feedback** (coming soon)

### 🛠️ Improvements

#### Installation Process
- **Robust error handling** during installation
- **Better progress reporting** and user feedback
- **Automatic dependency resolution**
- **Rollback capabilities** on installation failure

#### System Integration
- **Enhanced Windows service management**
- **Improved registry handling**
- **Better privilege escalation handling**
- **Comprehensive system compatibility checks**

#### Logging and Diagnostics
- **Enhanced logging system** with multiple levels
- **Better error reporting** with context information
- **Diagnostic tools** for troubleshooting
- **Installation verification** checks

### 🐛 Bug Fixes

- **Fixed:** `'DownloadManager' object has no attribute '_tracker'` error
- **Fixed:** VDD installation hanging on some systems
- **Fixed:** PowerShell execution policy issues
- **Fixed:** Installation tracking corruption
- **Fixed:** Service installation failures on newer Windows versions

### 📦 Dependencies

#### Updated Dependencies
- **CustomTkinter 5.2.0+** - Modern GUI framework
- **Requests 2.31.0+** - Enhanced HTTP handling
- **PSUtil 6.0.0+** - Better system monitoring

#### New Dependencies (In Development)
- **CustomTkinter** - GUI interface support (development branch only)
- **Threading enhancements** - Improved parallel processing

### 🔧 Technical Changes

#### Architecture Improvements
- **Refactored installation system** for better modularity
- **Improved error handling** throughout codebase
- **Better separation of concerns** between GUI and CLI
- **Enhanced configuration management**

#### Code Quality
- **Comprehensive documentation** updates
- **Type hints** added throughout codebase
- **Unit test coverage** improvements
- **Code formatting** standardization

### 📚 Documentation

#### New Documentation
- **Complete Wiki** with 10+ comprehensive guides
- **API Reference** for developers
- **Architecture Overview** technical documentation
- **Troubleshooting Guide** covering common issues

#### Updated Guides
- **Installation Guide** with step-by-step instructions
- **Steam Deck Guide** for portable gaming
- **HDR Configuration** for enhanced visuals
- **FAQ** addressing common questions

---

## 🎯 Version 0.3.1 - Complete Localization and Improved Workflows

**Release Date:** July 30, 2025

### ✨ New Features

#### Localization System
- **Multi-language support** framework implemented
- **French translation** complete
- **Dynamic language switching**
- **Extensible for additional languages**

#### Workflow Improvements
- **Enhanced menu system** with better navigation
- **Improved user experience** with clearer prompts
- **Better error messages** with actionable solutions
- **Streamlined installation process**

### 🛠️ Improvements

- **Better Sunshine detection** logic
- **Enhanced Playnite integration**
- **Improved VDD installation process**
- **Better system compatibility checks**

### 🐛 Bug Fixes

- **Fixed:** Language encoding issues
- **Fixed:** Menu navigation problems
- **Fixed:** Installation path detection
- **Fixed:** Service startup issues

---

## 🔧 Version 0.3.0 - Major Architecture Overhaul

**Release Date:** July 15, 2025

### ✨ New Features

#### Comprehensive Uninstaller System
- **Complete component removal** capability
- **Registry cleanup** and service removal
- **File system cleanup** with verification
- **Rollback support** for failed installations

#### Enhanced Component Management
- **Individual component** install/uninstall
- **Dependency management** between components
- **Version tracking** and update support
- **Configuration preservation** across updates

### 🛠️ Improvements

#### System Integration
- **Better Windows integration** with proper service handling
- **Enhanced security** with privilege management
- **Improved error recovery** mechanisms
- **Better system resource management**

#### User Experience
- **Clearer progress indicators**
- **Better error messages** with solutions
- **Improved installation feedback**
- **Enhanced logging and diagnostics**

### 🐛 Bug Fixes

- **Fixed:** Memory leaks during installation
- **Fixed:** Service installation failures
- **Fixed:** Path handling issues with spaces
- **Fixed:** Registry permission problems

---

## 🎮 Version 0.2.5 - Gaming Enhancements

**Release Date:** June 20, 2025

### ✨ New Features

#### Playnite Integration
- **Full Playnite support** with automated installation
- **Playnite Watcher** for enhanced streaming integration
- **Game library management** with metadata
- **Controller optimization** for couch gaming

#### Streaming Optimizations
- **HDR support** improvements
- **Better resolution handling**
- **Enhanced virtual display management**
- **Performance optimizations** for streaming

### 🛠️ Improvements

- **Faster download speeds** with parallel processing
- **Better network error handling**
- **Enhanced component verification**
- **Improved system requirements checking**

---

## 🖥️ Version 0.2.0 - Virtual Display Revolution

**Release Date:** May 15, 2025

### ✨ New Features

#### Virtual Display Driver Support
- **IDD Sample Driver** integration
- **Multi-virtual display** support
- **Custom resolution** configuration
- **HDR passthrough** capability

#### Sunshine Virtual Monitor
- **Advanced display management** with PowerShell scripts
- **Dynamic resolution matching**
- **Multi-monitor configuration** support
- **VSync control** integration

### 🛠️ Improvements

- **Modular installation system**
- **Better component isolation**
- **Enhanced error reporting**
- **Improved system compatibility**

---

## 🌟 Version 0.1.0 - Initial Release

**Release Date:** April 1, 2025

### ✨ Initial Features

#### Core Installation System
- **Sunshine streaming server** automated installation
- **Basic configuration** setup
- **Windows service** integration
- **Simple CLI interface**

#### Foundation Features
- **Download management** system
- **Basic error handling**
- **Installation verification**
- **System requirements checking**

---

## 🔄 Migration Guides

### Upgrading from 0.3.1 to 0.3.2

**Automatic Migration:**
- Installation tracker data is automatically migrated
- GUI components are automatically added
- Existing configurations are preserved

**Manual Steps:**
1. **Backup your configuration** before upgrading
2. **Run the new installer** - it will detect existing components
3. **Test streaming functionality** after upgrade
4. **Try the new GUI interface** with `python src/gui_main.py`

### Upgrading from 0.2.x to 0.3.x

**Breaking Changes:**
- **Configuration format** changes require manual migration
- **Service names** may have changed
- **Installation paths** may be different

**Migration Steps:**
1. **Export Sunshine configuration** before upgrade
2. **Uninstall previous version** using old uninstaller
3. **Clean install** new version
4. **Import previous configuration** via Sunshine Web UI
5. **Reconfigure applications** in Sunshine

### Upgrading from 0.1.x to 0.2.x

**Major Changes:**
- **Complete architecture rewrite**
- **New component system**
- **Virtual display support**

**Migration Required:**
1. **Complete uninstall** of 0.1.x version
2. **Clean installation** of 0.2.x version
3. **Reconfigure from scratch**

---

## 📋 Changelog Summary

### Version Comparison

| Feature | v0.1.0 | v0.2.0 | v0.3.0 | v0.3.1 | v0.3.2 |
|---------|--------|--------|--------|--------|--------|
| Sunshine Installation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Virtual Display Driver | ❌ | ✅ | ✅ | ✅ | ✅ |
| Sunshine Virtual Monitor | ❌ | ✅ | ✅ | ✅ | ✅ |
| Playnite Integration | ❌ | ❌ | ✅ | ✅ | ✅ |
| Complete Uninstaller | ❌ | ❌ | ✅ | ✅ | ✅ |
| Multi-language Support | ❌ | ❌ | ❌ | ✅ | ✅ |
| GUI Interface | ❌ | ❌ | ❌ | ❌ | 🚧 In Dev |
| Installation Tracking | ❌ | ❌ | Basic | ✅ | ✅ |

### Download Statistics

| Version | Downloads | Release Date | Support Status |
|---------|-----------|--------------|----------------|
| v0.3.2 | Current | Aug 5, 2025 | ✅ Active Support |
| v0.3.1 | 1,250+ | Jul 30, 2025 | ⚠️ Security Updates Only |
| v0.3.0 | 2,100+ | Jul 15, 2025 | ❌ End of Life |
| v0.2.5 | 1,800+ | Jun 20, 2025 | ❌ End of Life |
| v0.2.0 | 950+ | May 15, 2025 | ❌ End of Life |
| v0.1.0 | 500+ | Apr 1, 2025 | ❌ End of Life |

---

## 🎯 Upcoming Releases

### Version 0.4.0 (Planned - September 2025)
- **GUI Interface** - Complete graphical user interface
- **Web-based management interface**
- **Cloud configuration sync**
- **Advanced HDR management**
- **Performance monitoring dashboard**

### Version 0.5.0 (Planned - Q4 2025)
- **Multi-user support**
- **Network deployment tools**
- **Advanced security features**
- **Mobile management app**
- **Enterprise features**

---

*For technical details about any release, see the [Architecture Overview](Architecture-Overview) or [API Reference](API-Reference) documentation.*