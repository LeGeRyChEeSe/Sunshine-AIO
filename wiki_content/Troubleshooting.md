# Troubleshooting Guide

This guide addresses the most common issues reported by Sunshine-AIO users. Solutions are organized by category for easy navigation.

## ⚡ Quick Fix - Try Automatic Installation First

Most installation and setup issues are resolved by using the automated installer:
```powershell
# Run as Administrator - Installs Python, Git, and everything automatically
irm https://sunshine-aio.com/script.ps1 | iex
# No manual setup required - everything is handled automatically
```

**What it fixes automatically:**
- ✅ Missing Python or wrong Python version
- ✅ Missing Git installation
- ✅ PowerShell execution policy issues
- ✅ Missing dependencies and packages
- ✅ Incorrect environment setup
- ✅ Path and permission problems

## 🔥 Critical Issues (High Priority)

### Issue: Moonlight connects but games never start + PC stuttering
**Symptoms:** Connection establishes, but applications fail with "error -1", mouse becomes unresponsive during connection attempts.

**Causes:**
- PowerShell script failure in `setup_sunvdm.ps1`
- Display resolution mismatches
- Virtual display driver conflicts

**Solutions:**
1. **Check PowerShell Execution Policy:**
   ```powershell
   Get-ExecutionPolicy
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Manual Script Test:**
   ```powershell
   cd "tools\sunshine-virtual-monitor-main"
   .\setup_sunvdm.ps1 1920 1080 60 off
   ```

3. **Check Virtual Display Status:**
   ```powershell
   Get-PnpDevice -Class "Display" | Where-Object {$_.FriendlyName -like "*Virtual*"}
   ```

4. **Reset Display Configuration:**
   - Right-click Desktop → Display Settings
   - Reset to single monitor temporarily
   - Retry connection

### Issue: Playnite not opening after Sunshine-AIO installation
**Symptoms:** Playnite launches locally but fails via Moonlight with "error 0".

**Causes:**
- Global prep commands interfering with Playnite
- Virtual display driver incompatibility
- Incorrect app configuration in Sunshine

**Solutions:**
1. **Check Sunshine App Configuration:**
   ```json
   {
     "name": "Playnite",
     "cmd": "C:\\Program Files\\Playnite\\Playnite.FullscreenApp.exe",
     "prep-cmd": [],
     "detached": []
   }
   ```

2. **Disable Global Prep Commands Temporarily:**
   - Sunshine Web UI → Configuration
   - Uncheck "Global Prep Commands"
   - Test Playnite streaming

3. **Manual Playnite Test:**
   ```batch
   "C:\Program Files\Playnite\Playnite.FullscreenApp.exe"
   ```

### Issue: Display stuck in wrong resolution after streaming
**Symptoms:** Monitor resolution remains incorrect after client disconnect, especially on ultrawide displays.

**Causes:**
- Display reversion logic failure
- Windows display API issues
- Hardware-specific ultrawide problems

**Solutions:**
1. **Manual Display Reset:**
   ```powershell
   # Reset to original resolution
   displayswitch /extend
   displayswitch /internal
   ```

2. **Check Display Reversion Log:**
   ```
   Sunshine logs: C:\ProgramData\Sunshine\sunshine.log
   Look for: "Failed to revert display device configuration"
   ```

3. **Registry Display Fix (Advanced):**
   ```batch
   # Restart Windows Display Driver
   pnputil /restart-device "Root\BasicDisplay"
   ```

## 🛠️ Installation Issues (Medium Priority)

### Issue: Installer script fails and window closes immediately
**Symptoms:** PowerShell window flashes and closes, no error visible.

**Solutions:**
1. **Run with Debug Mode:**
   ```powershell
   powershell -NoExit -ExecutionPolicy Bypass -File install.ps1
   ```

2. **Check Python Installation:**
   ```batch
   python --version
   pip --version
   ```

3. **Manual Installation:**
   ```batch
   pip install -r requirements.txt
   python src/main.py
   ```

### Issue: Virtual Display Driver not working
**Symptoms:** No virtual display appears in display settings.

**Solutions:**
1. **Verify VDD Installation:**
   ```powershell
   Get-PnpDevice -Class "Display" | Select-Object FriendlyName, Status
   ```

2. **Manual VDD Control:**
   ```batch
   cd "tools\VDD Control"
   "VDD Control.exe"
   # Click "Install Driver"
   ```

3. **Check Device Manager:**
   - Open Device Manager
   - Look for "IDD HDR" under Display adapters
   - If yellow warning, update driver

### Issue: PowerShell script execution blocked
**Symptoms:** Scripts fail with "execution of scripts is disabled" error.

**Solutions:**
1. **Fix Execution Policy:**
   ```powershell
   # Run as Administrator
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
   ```

2. **Bypass for Single Script:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```

## 🎮 Gaming & Streaming Issues

### Issue: HDR not working on Steam Deck
**Symptoms:** HDR games appear washed out or incorrect colors.

**Solutions:**
1. **Check Steam Deck HDR Support:**
   - Steam Deck OLED: Supports HDR
   - Steam Deck LCD: Limited HDR support

2. **Sunshine HDR Configuration:**
   ```json
   {
     "hdr": true,
     "hdr_prep_cmd": "powershell.exe -file enable_hdr.ps1"
   }
   ```

3. **Manual HDR Test:**
   - Windows Settings → Display → HDR
   - Enable HDR manually
   - Test with HDR content

### Issue: Generic "error -1" when starting applications
**Symptoms:** All applications fail with the same error code.

**Solutions:**
1. **Check Application Paths:**
   ```json
   {
     "name": "Steam",
     "cmd": "C:\\Program Files (x86)\\Steam\\steam.exe",
     "working-dir": "C:\\Program Files (x86)\\Steam"
   }
   ```

2. **Test Command Manually:**
   ```batch
   # Run the exact command from Sunshine config
   "C:\Program Files (x86)\Steam\steam.exe" -bigpicture
   ```

3. **Check Sunshine Logs:**
   ```
   Location: C:\ProgramData\Sunshine\sunshine.log
   Look for: "Executing Do Cmd" and any error messages
   ```

## 🔧 Service & Configuration Issues

### Issue: Configuration breaks after Sunshine restart
**Symptoms:** Settings reset or applications disappear after service restart.

**Solutions:**
1. **Verify Configuration Persistence:**
   ```
   Check: C:\ProgramData\Sunshine\config.json
   Backup: Copy config files before restart
   ```

2. **Service Restart Test:**
   ```batch
   net stop SunshineService
   net start SunshineService
   ```

3. **Configuration Validation:**
   - Sunshine Web UI → Configuration → Validate
   - Fix any JSON syntax errors

### Issue: Display settings don't persist
**Symptoms:** Display configuration changes don't stick between sessions.

**Solutions:**
1. **Windows Display Persistence:**
   ```batch
   # Save current display config
   displayswitch /clone
   # Apply your preferred settings
   # Windows should remember them
   ```

2. **Check Display Profile:**
   - Windows Settings → Display → Advanced display
   - Ensure correct display profile is selected

## 📊 Performance Optimization

### Network Issues
```
Low latency settings:
- Bitrate: 20-30 Mbps for 1080p
- FPS: Match client display (usually 60)
- Encoder: NVENC (NVIDIA) or AMF (AMD)
```

### GPU Optimization
```
NVIDIA Settings:
- Enable GPU Hardware Acceleration
- Set Power Management to "Prefer Maximum Performance"
- Disable Windows GPU Scheduler if issues persist
```

### System Performance
```powershell
# Disable Windows Game Mode if causing issues
Get-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled"
Set-ItemProperty -Path "HKCU:\Software\Microsoft\GameBar" -Name "AutoGameModeEnabled" -Value 0
```

## 🆘 Getting Additional Help

### Collect System Information
```batch
# System info for support
systeminfo > system_info.txt
dxdiag /t dxdiag_info.txt
```

### Sunshine Logs Location
```
Main log: C:\ProgramData\Sunshine\sunshine.log
Service log: Windows Event Viewer → Applications and Services → Sunshine
```

### Before Reporting Issues
1. **Check existing issues:** [GitHub Issues](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues)
2. **Collect logs:** Include relevant log snippets
3. **System specs:** OS version, GPU, network setup
4. **Reproduction steps:** Exact steps to reproduce the issue

---
*If your issue isn't covered here, please [create a new issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new) with detailed information.*