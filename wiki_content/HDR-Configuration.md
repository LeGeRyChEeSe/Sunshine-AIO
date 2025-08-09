# HDR Configuration Guide

Complete guide for setting up High Dynamic Range (HDR) streaming with Sunshine-AIO.

## 🌟 HDR Overview

HDR provides:
- **Enhanced brightness range** - Brighter highlights, darker shadows
- **Wider color gamut** - More vivid and accurate colors  
- **Better visual realism** - Closer to real-world lighting
- **Gaming advantages** - Better visibility in dark/bright areas

## 📋 HDR Requirements

### Host PC Requirements

**Hardware:**
- **GPU:** NVIDIA GTX 1050+ or AMD RX 400+ with HDR support
- **Display:** HDR10-compatible monitor or TV
- **HDMI/DisplayPort:** HDMI 2.0a+ or DisplayPort 1.4+
- **Windows:** Windows 10 version 1709+ or Windows 11

**Software:**
- **Sunshine-AIO** with HDR components installed
- **Updated GPU drivers** (latest NVIDIA/AMD drivers)
- **Windows HDR enabled** in display settings

### Client Device Requirements

**Supported Clients:**
- **Windows:** HDR-capable display + Windows 10/11
- **Android:** HDR10 compatible device (Samsung Galaxy, Google Pixel, etc.)
- **Steam Deck OLED:** Native HDR support (LCD model has limited support)
- **Apple devices:** Limited HDR support in Moonlight
- **Smart TVs:** HDR10-compatible with Moonlight app

## 🛠️ Windows HDR Setup

### Enable HDR on Host PC

**Method 1: Windows Settings**
```
1. Settings → System → Display
2. Select your HDR display
3. Toggle "Use HDR" to On
4. Configure HDR settings
```

**Method 2: PowerShell**
```powershell
# Check HDR capability
Get-WmiObject -Class Win32_VideoController | Select-Object Name, VideoModeDescription

# Enable HDR (requires admin)
# Windows will prompt for HDR settings
```

### Verify HDR Installation

**Check Display Capabilities:**
```
1. Settings → System → Display → Advanced display
2. Look for "HDR10" or "Dolby Vision" support
3. Check color depth: Should be 10-bit or higher
4. Verify refresh rate: 60Hz minimum recommended
```

**Test HDR Content:**
```
1. Microsoft Store → Movies & TV app
2. Search for HDR content samples
3. Play and verify enhanced visuals
4. Or use YouTube HDR test videos
```

## 🎯 Sunshine HDR Configuration

### Enable HDR in Sunshine

**Web UI Configuration:**
```
1. Open Sunshine Web UI: https://localhost:47990
2. Configuration → Video
3. Enable "HDR Support"
4. Set "Color Range": Full (0-255)
5. Set "Color Space": Rec. 2020 (for HDR)
```

**Advanced HDR Settings:**
```json
{
  "hdr": true,
  "hdr_prep_cmd": [
    "powershell.exe -file enable_hdr.ps1"
  ],
  "hdr_stop_cmd": [
    "powershell.exe -file disable_hdr.ps1"  
  ]
}
```

### HDR Prep Commands

**Create HDR Management Script:**
```powershell
# enable_hdr.ps1
param(
    [string]$ClientWidth = $env:SUNSHINE_CLIENT_WIDTH,
    [string]$ClientHeight = $env:SUNSHINE_CLIENT_HEIGHT,
    [string]$ClientHDR = $env:SUNSHINE_CLIENT_HDR
)

if ($ClientHDR -eq "1") {
    Write-Host "Client supports HDR, enabling HDR mode"
    # Enable HDR via Windows API or registry
    # Set appropriate color space and bit depth
} else {
    Write-Host "Client does not support HDR, using SDR mode"
}
```

**Disable HDR Script:**
```powershell
# disable_hdr.ps1
Write-Host "Disabling HDR and restoring original display settings"
# Restore original display configuration
# Reset color space to sRGB
```

## 🎮 Game-Specific HDR Configuration

### Steam Games

**Enable HDR in Steam:**
```
1. Steam → Settings → In-Game
2. Enable "Use HDR when available"
3. Per-game: Properties → General → Launch Options
4. Add: -hdr (if game supports it)
```

**Popular HDR Games:**
- **Cyberpunk 2077** - Excellent HDR implementation
- **Resident Evil 4** - Great HDR visuals
- **Forza Horizon 5** - Outstanding HDR racing
- **Assassin's Creed Valhalla** - Good HDR support
- **Metro Exodus Enhanced** - Reference HDR quality

### Game Launchers

**Epic Games Store:**
```
HDR automatically detected when Windows HDR is enabled
No additional configuration needed for most games
```

**Xbox Game Pass:**
```
1. Xbox app → Settings → General
2. Enable "HDR for games"
3. Individual games may have HDR options
```

### HDR Game Settings

**Typical HDR Options:**
```
HDR Mode: HDR10 (most compatible)
Peak Brightness: Match your display (400-4000 nits)
Paper White: 100-200 nits (recommended starting point)
Color Gamut: Wide/DCI-P3/Rec.2020
Tone Mapping: Game-dependent (Auto/ACES/etc.)
```

## 📱 Client HDR Configuration

### Moonlight HDR Settings

**Windows Moonlight Client:**
```
Settings → Streaming:
- HDR: Enable
- Color Space: Rec. 2020
- Color Range: Full
- HDR Tone Mapping: Reinhard or ACES
```

**Android Moonlight:**
```
Settings → Video:
- Enable HDR streaming: On
- HDR Tone Mapping: Balanced
- Color Space: Auto (or Force HDR10)
```

### Steam Deck HDR

**Steam Deck OLED:**
```
Steam → Settings → Display → HDR
Enable HDR: On
HDR Brightness: Adjust to preference (usually 400-600 nits)
Color Gamut: Wide color gamut
```

**Steam Deck LCD (Limited Support):**
```
HDR support is minimal on LCD model
Better to stream in SDR for consistent experience
Consider tone mapping on host PC instead
```

## 🔧 Advanced HDR Configuration

### Custom Display Profiles

**Create HDR Profile:**
```
Windows Color Management:
1. Control Panel → Color Management
2. Create new profile for HDR streaming
3. Set appropriate color space (Rec.2020)
4. Configure gamma curve for HDR
```

**PowerShell Display Management:**
```powershell
# Get display information
Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorBasicDisplayParams

# Set HDR color profile
$ColorProfile = "HDR_Profile.icm"
Set-WmiInstance -Class Win32_SystemColorProfile -Arguments @{TargetPath=$ColorProfile}
```

### Network Optimization for HDR

**Increased Bandwidth Requirements:**
```
SDR Streaming: 10-20 Mbps typical
HDR Streaming: 25-50 Mbps recommended
4K HDR Streaming: 50-100 Mbps for best quality

Network Settings:
- Use wired connection when possible
- QoS prioritization for streaming traffic
- Buffer size optimization for HDR content
```

**Sunshine HDR Bitrate:**
```json
{
  "bitrate": 30000,
  "hdr_bitrate_multiplier": 1.5,
  "keyframe_interval": 30
}
```

## 🛠️ Troubleshooting HDR Issues

### Common HDR Problems

**HDR Not Available in Moonlight:**
```
Check:
1. Windows HDR enabled on host
2. HDR-capable display on client
3. Updated GPU drivers
4. HDMI/DP cable supports HDR bandwidth
5. Moonlight client version supports HDR
```

**Washed Out Colors:**
```
Solutions:
1. Adjust HDR brightness in game settings
2. Check paper white levels (100-200 nits)
3. Verify color range setting (Full vs Limited)
4. Try different tone mapping options
```

**Performance Issues with HDR:**
```
Optimizations:
1. Lower resolution while keeping HDR
2. Reduce bitrate slightly
3. Use hardware encoding (NVENC/AMF)
4. Close unnecessary background apps
5. Use Game Mode on Windows
```

### Steam Deck Specific Issues

**HDR Not Working on Steam Deck OLED:**
```
Troubleshooting:
1. Ensure SteamOS is updated (3.5+)
2. Enable HDR in Steam settings
3. Check Moonlight HDR settings
4. Verify network bandwidth (30+ Mbps)
5. Test with known HDR content
```

**Color Accuracy Issues:**
```
1. Calibrate Steam Deck display
2. Adjust HDR brightness settings
3. Use balanced tone mapping
4. Consider streaming in SDR if issues persist
```

### Network and Performance

**HDR Streaming Lag:**
```
Solutions:
1. Increase buffer size in Moonlight
2. Use hardware decoding on client
3. Lower HDR quality temporarily
4. Check for network congestion
5. Use 5GHz WiFi or wired connection
```

## 📊 HDR Quality Assessment

### Testing HDR Quality

**HDR Test Content:**
```
YouTube HDR Videos:
- "HDR 10-bit Test Pattern"
- "4K HDR Nature Scenes"
- "HDR Gaming Footage"

Test Games:
- Ori and the Will of the Wisps (excellent HDR)
- Shadow of the Tomb Raider (good HDR implementation)
- Forza Horizon 5 (reference HDR quality)
```

**Quality Metrics:**
```
Good HDR Streaming:
- No visible banding in gradients
- Bright highlights without clipping
- Deep shadows with retained detail
- Vivid colors without oversaturation
- Smooth motion in HDR content
```

### Optimization Guidelines

**Host PC Optimization:**
```
GPU Settings:
- NVIDIA: Enable HDR in NVCP
- AMD: Enable HDR in Radeon Software
- Intel: Enable HDR in Intel Graphics Command Center

Windows Settings:
- Game Mode: On
- Hardware-accelerated GPU scheduling: On
- Variable refresh rate: Off during streaming
```

**Client Optimization:**
```
Display Settings:
- Match native resolution when possible
- Enable VRR/FreeSync if supported
- Adjust HDR brightness to room lighting
- Use proper viewing distance for HDR effect
```

## 🎯 HDR Streaming Profiles

### Quality Presets

**Ultra Quality (Local Network):**
```json
{
  "resolution": "3840x2160",
  "fps": 60,
  "bitrate": 80000,
  "hdr": true,
  "encoder": "h265_nvenc"
}
```

**High Quality (Fast Network):**
```json
{
  "resolution": "2560x1440", 
  "fps": 60,
  "bitrate": 40000,
  "hdr": true,
  "encoder": "h264_nvenc"
}
```

**Balanced (Standard Network):**
```json
{
  "resolution": "1920x1080",
  "fps": 60, 
  "bitrate": 25000,
  "hdr": true,
  "encoder": "h264_nvenc"
}
```

---

*For device-specific HDR setup, see the [Steam Deck Guide](Steam-Deck-Guide) or check the [Troubleshooting](Troubleshooting) section for HDR-related issues.*