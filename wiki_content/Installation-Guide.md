# Complete Installation Guide

This comprehensive guide covers all installation methods and configuration options for Sunshine-AIO.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- **OS:** Windows 10 (version 1903+) or Windows 11
- **CPU:** 64-bit processor with 2+ cores
- **RAM:** 4GB available memory
- **GPU:** DirectX 11 compatible graphics card
- **Storage:** 2GB free space
- **Network:** Broadband internet connection

**Recommended Setup:**
- **OS:** Windows 11 (latest updates)
- **CPU:** Modern multi-core processor (Intel i5/AMD Ryzen 5+)
- **RAM:** 8GB+ system memory
- **GPU:** Hardware encoding support (NVIDIA GTX 1050+, AMD RX 400+)
- **Storage:** SSD with 5GB+ free space
- **Network:** Gigabit ethernet connection

### Required Permissions
- **Administrator privileges** for installation

*Note: Python 3.8+, Git, and PowerShell execution permissions will be automatically handled by the installation script*

## 🚀 Installation Methods

### Method 1: One-Line PowerShell (Fastest & Recommended)

**Single Command Installation:**
```powershell
# Run as Administrator - This will automatically download and install
irm https://sunshine-aio.com/script.ps1 | iex
```

**What it does automatically:**
- ✅ **Checks system requirements** and compatibility
- ✅ **Installs Python 3.8+** if not already present
- ✅ **Installs Git** if not already present
- ✅ **Downloads latest Sunshine-AIO** from GitHub repository
- ✅ **Creates Python virtual environment** for isolation
- ✅ **Installs all required packages** (requests, psutil, etc.)
- ✅ **Sets up project structure** and creates shortcuts
- ✅ **Guides through component selection** interactively
- ✅ **Configures everything** for immediate use

**User interaction required:**
- Choose installation directory (default provided)
- Select components to install (Sunshine, VDD, Playnite, etc.)
- Configure Sunshine settings when prompted

### Method 2: Manual Installation (Advanced Users)

**For developers or users who prefer manual control:**

**Step 1: Download Repository**
```bash
# Manually download from GitHub
https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases
# Extract to desired location
```

**Step 2: Manual Setup**
```powershell
# Install Python 3.8+ manually if needed
# Install Git manually if needed
# Create virtual environment
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

**Note:** Method 1 (one-line PowerShell) is strongly recommended as it handles all these steps automatically.

### Method 3: Legacy/Development Mode

**Only use if you already have the repository and want to run directly:**
```batch
# Ensure you have the repository downloaded
# Ensure Python 3.8+ is installed
python --version

# Install required packages
pip install -r requirements.txt

# Run as Administrator
python src/main.py
```

**Note:** This method requires manual setup of Python environment and dependencies.

### Method 4: GUI Interface (In Development)

**Coming Soon:**
- Graphical interface using CustomTkinter
- Visual component selection
- Real-time installation progress monitoring
- Modern, user-friendly design

**Current Status:** GUI interface is being developed and will be available in a future release.

## 🎛️ Component Selection

### Core Components

#### 🌞 Sunshine (Required)
**What it does:** Main streaming server that captures and transmits your screen
**Installation:** 
- Downloads official Sunshine installer
- Installs as Windows service
- Configures firewall rules
- Sets up web UI access

**Configuration:**
```json
{
  "hostname": "your-pc-name",
  "port": 47989,
  "cert": "sunshine.cert",
  "key": "sunshine.key"
}
```

#### 🖥️ Virtual Display Driver (Recommended)
**What it does:** Creates virtual monitors for independent streaming
**Benefits:**
- Stream without affecting your main display
- Custom resolutions for different clients
- Multiple virtual displays support
- HDR passthrough capability

**Installation Process:**
1. Downloads IDD Sample Driver
2. Installs driver certificates
3. Creates virtual display device
4. Configures display profiles

### Optional Components

#### 📱 Sunshine Virtual Monitor (Advanced)
**What it does:** Advanced virtual display management with PowerShell scripts
**Features:**
- Dynamic resolution matching
- HDR on/off switching
- Multi-monitor configuration
- Client-specific display setups

**Installation Includes:**
- PowerShell management scripts
- Multi Monitor Tool integration
- VSync Toggle utility
- Display configuration automation

#### 🎮 Playnite (Game Library)
**What it does:** Unified game library manager for all gaming platforms
**Supports:**
- Steam, Epic Games Store, GOG
- Xbox Game Pass, Origin, Uplay
- Emulators and standalone games
- Custom game categories

**Configuration Options:**
- Fullscreen mode optimization
- Controller support setup
- Theme customization
- Metadata scraping

#### 👁️ Playnite Watcher (Stream Integration)
**What it does:** Enhances Playnite with streaming-specific features
**Features:**
- Automatic game detection
- Stream session logging
- Performance monitoring
- Integration helpers

## ⚙️ Installation Configuration

### Interactive Setup Options

**Component Selection Screen:**
```
Select components to install:
[X] Sunshine (Required)
[X] Virtual Display Driver (Recommended)  
[ ] Sunshine Virtual Monitor (Advanced)
[ ] Playnite (Optional)
[ ] Playnite Watcher (Optional)
```

**Advanced Options:**
- Custom installation directories
- Service configuration
- Network settings
- Display preferences

### Silent Installation

For automated deployments:
```json
{
  "components": ["sunshine", "vdd"],
  "sunshine_options": {
    "port": 47989,
    "auto_start": true
  },
  "vdd_options": {
    "resolution": "1920x1080",
    "refresh_rate": 60
  }
}
```

Run with: `python src/main.py --config config.json --silent`

## 🔧 Post-Installation Configuration

### 1. Sunshine Web UI Setup

**Access the Web Interface:**
1. Open browser: `https://localhost:47990`
2. Accept certificate warning (self-signed)
3. Create admin account
4. Configure basic settings

**Essential Settings:**
```
Username: [your-choice]
Password: [secure-password]
Output Resolution: Auto (or match your display)
FPS: 60
Bitrate: 20000 (adjust for network)
```

### 2. Add Applications

**Desktop Streaming:**
```json
{
  "name": "Desktop",
  "cmd": "cmd /C",
  "working-dir": "C:\\"
}
```

**Steam Big Picture:**
```json
{
  "name": "Steam Big Picture",
  "cmd": "C:\\Program Files (x86)\\Steam\\steam.exe",
  "args": "-bigpicture",
  "working-dir": "C:\\Program Files (x86)\\Steam"
}
```

**Individual Game:**
```json
{
  "name": "Game Name",
  "cmd": "C:\\Games\\YourGame\\game.exe",
  "working-dir": "C:\\Games\\YourGame",
  "prep-cmd": ["taskkill /f /im explorer.exe"],
  "detached": ["explorer.exe"]
}
```

### 3. Network Configuration

**Automatic (Recommended):**
- UPnP will configure port forwarding
- mDNS enables auto-discovery
- Certificate generation is automatic

**Manual Configuration:**
```
Router Port Forwarding:
- Internal Port: 47989 (TCP/UDP)
- External Port: 47989 (TCP/UDP)
- Internal IP: [Your PC IP]

Firewall Rules:
- Allow Sunshine through Windows Firewall
- Allow port 47989 inbound/outbound
```

### 4. Virtual Display Setup

**Verify Installation:**
```powershell
# Check for virtual display
Get-PnpDevice -Class "Display" | Where-Object {$_.FriendlyName -like "*Virtual*"}

# Should show: IDD HDR (Virtual Display)
```

**Configure Resolutions:**
1. Right-click Desktop → Display Settings
2. Virtual display should appear as secondary
3. Set desired resolution and position
4. Apply changes

## 🧪 Testing Your Installation

### Basic Functionality Test

**1. Service Status:**
```powershell
Get-Service -Name "SunshineService"
# Should show: Running
```

**2. Web UI Access:**
- Navigate to `https://localhost:47990`
- Should load Sunshine configuration page
- No certificate errors after accepting

**3. Virtual Display:**
- Check display settings for virtual monitor
- Should see additional display available
- Test resolution changes

### Streaming Test

**1. Install Moonlight Client:**
- Download from: https://moonlight-stream.org
- Install on target device
- Ensure same network as host PC

**2. Pairing Process:**
```
1. Launch Moonlight on client
2. Scan for PC (should auto-detect)
3. Enter pairing PIN from Sunshine Web UI
4. Successful pairing confirmation
```

**3. Stream Test:**
```
1. Launch "Desktop" application from Moonlight
2. Should see your PC screen on client
3. Test mouse/keyboard input
4. Verify audio streaming
```

## 🛠️ Troubleshooting Installation

### Common Installation Errors

**PowerShell Execution Policy Error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Python Not Found:**
```batch
# Install Python 3.8+ from python.org
# Or use Microsoft Store version
# Verify with: python --version
```

**Admin Privileges Required:**
```
Right-click PowerShell/Command Prompt
Select "Run as Administrator"
Re-run installation command
```

### Component-Specific Issues

**Sunshine Service Won't Start:**
```powershell
# Check Windows Event Viewer
eventvwr.msc
# Navigate to: Applications and Services → Sunshine
# Look for error messages
```

**Virtual Display Driver Failed:**
```powershell
# Manual driver installation
cd "tools\VDD Control"
.\VDD Control.exe
# Click "Install Driver" button
# Restart if prompted
```

**Playnite Installation Issues:**
```
# Check if Visual C++ Redistributable is installed
# Download from Microsoft if missing
# Retry Playnite installation
```

## 📁 Installation Directories

**Default Locations:**
```
Sunshine: C:\Program Files\Sunshine
VDD Control: [project]\tools\VDD Control  
Playnite: C:\Program Files\Playnite
SVM Tools: [project]\tools\sunshine-virtual-monitor-main
Config Data: C:\ProgramData\Sunshine
```

**Log Files:**
```
Installation: [project]\logs\installation.log
Sunshine: C:\ProgramData\Sunshine\sunshine.log
System Events: Windows Event Viewer → Sunshine
```

## 🔄 Updating Sunshine-AIO

### Update Process

**1. Backup Current Setup:**
```batch
# Export Sunshine configuration
# Backup installation tracker
copy "src\misc\variables\installation_tracker.json" backup_tracker.json
```

**2. Download New Version:**
```bash
git pull origin main
# Or download latest release ZIP
```

**3. Run Update:**
```batch
python src/main.py
# Select "Update components" option
```

**4. Restore Settings:**
```
Import previous Sunshine configuration
Verify all applications still work
Test streaming functionality
```

## 🚨 Security Considerations

### Network Security
- **Change default passwords** immediately
- **Use strong certificates** for HTTPS
- **Configure firewall rules** appropriately
- **Monitor access logs** regularly

### System Security
- **Run with minimal privileges** when possible
- **Keep components updated**
- **Regular security scans**
- **Monitor system resources**

---

*For advanced configuration options, see [Architecture Overview](Architecture-Overview) and [API Reference](API-Reference).*