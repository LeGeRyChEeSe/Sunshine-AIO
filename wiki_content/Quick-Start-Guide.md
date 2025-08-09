# Quick Start Guide

Get Sunshine-AIO running in just 5 minutes! This guide covers the essential steps for a basic streaming setup.

## ⚡ Prerequisites

- **Windows 10/11** (64-bit)
- **Administrator privileges** required
- **Stable internet connection**
- **Moonlight client** on your streaming device

*Note: Python and Git will be automatically installed if not present*

## 🚀 Installation Steps

### 1. One-Line Installation (Recommended)
```powershell
# Run as Administrator - This does everything automatically
irm https://sunshine-aio.com/script.ps1 | iex
```

**What the script does automatically:**
- ✅ Checks and installs Python 3.8+ if needed
- ✅ Checks and installs Git if needed
- ✅ Downloads the latest Sunshine-AIO from GitHub
- ✅ Creates Python virtual environment
- ✅ Installs all required packages
- ✅ Sets up project structure and shortcuts
- ✅ Guides you through component selection

### 2. Alternative: Manual Installation
```bash
# Only if you prefer manual setup
# Download from: https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases
# Extract and run: python src/main.py

# Note: GUI interface in development (coming soon!)
```

### 2. Basic Configuration
When prompted, select these components for a quick setup:

- ✅ **Sunshine** (Required)
- ✅ **Virtual Display Driver** (Recommended)
- ⏹️ **Sunshine Virtual Monitor** (Skip for now)
- ⏹️ **Playnite** (Skip for now)
- ⏹️ **Playnite Watcher** (Skip for now)

### 3. Configure Sunshine
1. Open **Sunshine Web UI**: `https://localhost:47990`
2. Set a **username and password**
3. Add your first application:
   ```
   Name: Desktop
   Command: cmd /C
   Working Directory: C:\
   ```

### 4. Connect with Moonlight
1. Install **Moonlight** on your client device
2. **Scan for PC** or enter your host IP manually
3. **Pair** using the PIN displayed in Sunshine
4. **Launch** the Desktop application

## ✅ Verify Installation

### Check if services are running:
```powershell
# Check Sunshine service
Get-Service -Name "SunshineService"

# Check if virtual display is available
Get-PnpDevice -Class "Display" | Where-Object {$_.FriendlyName -like "*Virtual*"}
```

### Test streaming:
1. Launch **Desktop** from Moonlight
2. You should see your PC screen
3. Mouse and keyboard should work normally

## 🔧 Next Steps

Once basic streaming works:

1. **[Install Playnite](Playnite-Setup)** for game library management
2. **[Configure HDR](HDR-Configuration)** if you have HDR displays
3. **[Add more applications](Installation-Guide#adding-applications)** to stream
4. **[Optimize settings](Troubleshooting#performance-optimization)** for your network

## ⚠️ Common Quick Issues

### "Connection failed" in Moonlight
- **Check Windows Firewall** - Allow Sunshine through firewall
- **Verify network** - Both devices on same network
- **Check port 47989** - Default streaming port

### "No displays available" error
- **Run as Administrator** - VDD requires admin privileges
- **Restart after VDD install** - Some systems need reboot
- **Check display settings** - Virtual display should appear

### Performance issues
- **Adjust bitrate** in Sunshine settings (default: 20 Mbps)
- **Change resolution** to match client display
- **Close unnecessary programs** on host PC

## 🆘 Still Having Issues?

- **[Full Troubleshooting Guide](Troubleshooting)**
- **[Check FAQ](FAQ)**
- **[Report an Issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues)**

---
*Need more detailed setup? See the [complete Installation Guide](Installation-Guide)*