# Migration Guide

Complete guide for upgrading between Sunshine-AIO versions and migrating from other streaming solutions.

## 🔄 Version Upgrade Paths

### Current Version: 0.3.2

#### From 0.3.1 to 0.3.2 (Recommended Upgrade)

**What's New:**
- Enhanced installation tracking system
- New GUI interface (beta)
- Improved VDD support
- Better error handling and logging

**Migration Steps:**
```bash
# Method 1: Automatic Update (Fastest)
irm https://sunshine-aio.com/script.ps1 | iex
# When prompted, provide your existing Sunshine-AIO installation path
# The script will automatically backup, update, and preserve configurations

# Method 2: Manual Update
# 1. Backup current configuration
copy "C:\ProgramData\Sunshine\*" "C:\Backup\Sunshine\"
copy "src\misc\variables\installation_tracker.json" "C:\Backup\"

# 2. Download new version
git pull origin main
# Or download latest release

# 3. Run upgrade
python src/main.py
# Select "Update components" option

# 4. Verify installation
python src/main.py  # Test updated CLI interface
```

**Automatic Migration Features:**
- ✅ **Configuration preserved** - Sunshine settings maintained
- ✅ **Installation tracking** - Existing components detected
- ✅ **Service continuity** - No service interruption
- ✅ **Application configs** - Game applications preserved

**Manual Verification:**
```bash
# Check service status
Get-Service -Name "SunshineService"

# Verify applications still work
# Test streaming with Moonlight

# Check installation tracking
# Review installation_tracker.json for completeness
```

#### From 0.3.0 to 0.3.2 (Major Update)

**Breaking Changes:**
- Installation tracker format updated
- Enhanced dependency management
- Some configuration paths changed

**Migration Process:**
```bash
# 1. Full backup (IMPORTANT)
robocopy "C:\ProgramData\Sunshine" "C:\Backup\Sunshine" /E /COPYALL
robocopy "src" "C:\Backup\Sunshine-AIO-src" /E

# 2. Export Sunshine configuration
# Sunshine Web UI → Configuration → Export

# 3. Clean installation (recommended)
python src/main.py
# Select "Uninstall all components"

# 4. Fresh installation
git pull origin main
python src/main.py
# Install desired components

# 5. Import configuration
# Sunshine Web UI → Configuration → Import
```

#### From 0.2.x to 0.3.2 (Major Architecture Change)

**Critical Changes:**
- Complete uninstaller system added
- Component tracking completely rewritten
- Service management improved
- New dependency requirements

**Required Migration:**
```bash
# 1. Document current configuration
# Screenshot Sunshine Web UI settings
# List installed games/applications
# Note custom configurations

# 2. Complete removal of old version
# Manually uninstall components
# Clean registry entries
# Remove service files

# 3. Fresh installation
# Download v0.3.2
# Install with clean slate
# Reconfigure applications
```

### Legacy Version Upgrades

#### From 0.1.x to Current (Complete Rebuild)

**Architecture Changes:**
- Single-file installer → Modular component system
- Basic installation → Advanced tracking
- Manual setup → Automated configuration
- No VDD support → Full virtual display integration

**Migration Strategy:**
```bash
# Complete replacement required
# 1. Backup Sunshine configuration manually
# 2. Uninstall old version completely
# 3. Install current version fresh
# 4. Reconfigure from documentation
```

## 🔧 Component-Specific Migration

### Sunshine Configuration Migration

**Configuration Locations:**
```
Old location: Various scattered files
New location: C:\ProgramData\Sunshine\

Files to preserve:
- config.json (main configuration)
- apps.json (application list)  
- sunshine.cert & sunshine.key (certificates)
- credentials.json (user accounts)
```

**Automated Migration:**
```python
# Migration script included in v0.3.2
from src.misc.Config import Config

config = Config()
config.migrate_sunshine_config()
```

**Manual Migration:**
```json
// Old format example
{
  "sunshine_name": "MyPC",
  "port": 47989
}

// New format (auto-migrated)
{
  "sunshine": {
    "name": "MyPC", 
    "port": 47989,
    "install_path": "C:\\Program Files\\Sunshine",
    "version": "detected"
  }
}
```

### Virtual Display Driver Migration

**VDD Updates:**
- v0.2.x: Basic VDD Control integration
- v0.3.x: Enhanced driver management
- v0.3.2: Improved installation tracking

**Migration Process:**
```bash
# Check current VDD status
Get-PnpDevice -Class "Display" | Where-Object {$_.FriendlyName -like "*Virtual*"}

# If VDD exists but not tracked:
python src/main.py
# Select "Detect existing installations"
# System will scan and track existing VDD
```

### Playnite Integration Migration

**Playnite Versions:**
- v0.3.0+: Playnite + Playnite Watcher support
- v0.3.2: Enhanced integration tracking

**Migration Steps:**
```bash
# Preserve Playnite library
# Location: C:\Users\[user]\AppData\Roaming\Playnite

# Backup library database
copy "%AppData%\Playnite\library\*" "C:\Backup\Playnite\"

# Migration will preserve:
# - Game library data
# - Custom categories
# - Metadata and artwork
# - Controller configurations
```

## 🏠 Migrating from Other Streaming Solutions

### From Native Sunshine Installation

**Coming from standalone Sunshine:**

**Pre-Migration Assessment:**
```bash
# Check current Sunshine installation
Get-Service -Name "SunshineService"
ls "C:\Program Files\Sunshine"

# Check configuration
dir "C:\ProgramData\Sunshine"

# List applications
# Check apps.json content
```

**Migration Process:**
```bash
# 1. Backup existing configuration
robocopy "C:\ProgramData\Sunshine" "C:\Backup\Sunshine-Standalone" /E

# 2. Stop Sunshine service
net stop SunshineService

# 3. Install Sunshine-AIO
python src/main.py
# Select "Detect existing Sunshine installation"
# System will incorporate existing setup

# 4. Verify migration
# Test existing applications
# Check service functionality
```

### From NVIDIA GameStream (Legacy)

**GameStream Differences:**
- NVIDIA proprietary → Open source Sunshine
- Limited to NVIDIA GPUs → Any modern GPU
- GeForce Experience required → Standalone operation

**Migration Benefits:**
- ✅ **Better performance** with modern codecs
- ✅ **More flexibility** in configuration
- ✅ **Active development** and updates
- ✅ **Community support** and features

**Migration Steps:**
```bash
# 1. Document GameStream settings
# Screenshot resolution/bitrate settings
# List configured games

# 2. Disable GameStream
# NVIDIA Control Panel → GameStream → Disable

# 3. Install Sunshine-AIO
python src/main.py
# Full installation with all components

# 4. Configure equivalent settings
# Use GameStream settings as reference
# Configure games in Sunshine Web UI
```

### From Parsec

**Parsec vs Sunshine Comparison:**
```
Feature              | Parsec      | Sunshine-AIO
--------------------|-------------|-------------
Open Source         | No          | Yes
Local Network Only  | No          | Configurable  
GPU Requirements    | Flexible    | Modern GPU recommended
Virtual Displays    | Limited     | Full VDD support
Gaming Focus        | General     | Gaming optimized
```

**Migration Considerations:**
```bash
# Parsec advantages to consider:
# - Cloud streaming capability
# - Team/business features
# - Cross-platform hosting

# Sunshine-AIO advantages:
# - No cloud dependency
# - Better gaming performance
# - Open source flexibility
# - Virtual display integration
```

**Configuration Mapping:**
```json
// Parsec settings → Sunshine equivalent
{
  "resolution": "1920x1080",     // Direct mapping
  "fps": 60,                     // Direct mapping  
  "bitrate": "25000",            // Parsec kbps → Sunshine kbps
  "codec": "h264_nvenc",         // Hardware encoding
  "hdr": false                   // HDR support
}
```

### From Steam Remote Play

**When to Consider Migration:**
- ✅ **Non-Steam games** streaming needed
- ✅ **Better quality** control desired
- ✅ **Virtual displays** required
- ✅ **Local network** only usage
- ❌ **Steam ecosystem** integration sufficient

**Migration Process:**
```bash
# Steam Remote Play settings to document:
# - Resolution preferences
# - Bitrate settings
# - Controller configurations
# - Game-specific optimizations

# Install Sunshine-AIO with Steam integration:
python src/main.py
# Select Sunshine + Steam integration components

# Configure Steam in Sunshine:
# Add Steam Big Picture as application
# Configure controller support
# Test game streaming
```

## 🛠️ Troubleshooting Migration Issues

### Common Migration Problems

#### Configuration Not Preserved

**Issue:** Settings lost during upgrade

**Solutions:**
```bash
# Check backup location
dir "C:\ProgramData\Sunshine.backup"

# Manual restore
robocopy "C:\ProgramData\Sunshine.backup" "C:\ProgramData\Sunshine" /E

# Re-import configuration
# Sunshine Web UI → Configuration → Import
```

#### Service Installation Failure

**Issue:** SunshineService won't start after migration

**Solutions:**
```bash
# Check service status
sc query SunshineService

# Reinstall service
sc delete SunshineService
python src/main.py
# Reinstall Sunshine component

# Check Windows Event Viewer for errors
eventvwr.msc
```

#### Virtual Display Not Working

**Issue:** VDD not detected after migration

**Solutions:**
```bash
# Check device manager
devmgmt.msc
# Look for "IDD HDR" under Display adapters

# Reinstall VDD
python src/main.py
# Select "Reinstall Virtual Display Driver"

# Manual VDD installation
cd "tools\VDD Control"
"VDD Control.exe"
```

#### Applications Missing

**Issue:** Configured applications don't appear

**Solutions:**
```bash
# Check apps.json
type "C:\ProgramData\Sunshine\apps.json"

# Restore from backup
copy "C:\Backup\Sunshine\apps.json" "C:\ProgramData\Sunshine\"

# Restart Sunshine service
net stop SunshineService
net start SunshineService
```

### Recovery Procedures

#### Complete Migration Failure

**Recovery Steps:**
```bash
# 1. Stop all services
net stop SunshineService

# 2. Restore from backup
robocopy "C:\Backup\Sunshine" "C:\ProgramData\Sunshine" /E /PURGE

# 3. Clean installation
python src/main.py
# Select "Uninstall all components"
# Then reinstall with original settings
```

#### Partial Installation State

**Issue:** Some components installed, others failed

**Recovery:**
```bash
# Check installation status
python src/main.py
# Select "Status and diagnostics"

# Review installation tracker
type "src\misc\variables\installation_tracker.json"

# Selective reinstallation
python src/main.py
# Install only missing components
```

## 📊 Migration Checklist

### Pre-Migration Checklist

```bash
✅ Backup Sunshine configuration directory
✅ Export Sunshine applications list  
✅ Document custom settings and passwords
✅ Test current streaming functionality
✅ Check available disk space (2GB minimum)
✅ Verify administrator privileges
✅ Close Moonlight and streaming applications
✅ Stop background processes (Discord, etc.)
```

### Post-Migration Verification

```bash
✅ Sunshine service running
✅ Web UI accessible (https://localhost:47990)
✅ Applications list populated
✅ Virtual display available (if applicable)
✅ Streaming test successful
✅ Controller functionality verified
✅ Performance comparable or better
✅ All desired components tracked in installation_tracker.json
```

### Rollback Plan

**If migration fails:**
```bash
# 1. Stop new installation
net stop SunshineService

# 2. Restore backup
robocopy "C:\Backup\Sunshine" "C:\ProgramData\Sunshine" /E /PURGE

# 3. Reinstall previous version (if available)
# Download previous release from GitHub

# 4. Report issue with logs
# Create GitHub issue with:
# - Migration steps attempted
# - Error messages encountered
# - System information
# - Installation logs
```

---

*For specific migration issues, check the [Troubleshooting Guide](Troubleshooting) or [create a GitHub issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new) with your migration details.*