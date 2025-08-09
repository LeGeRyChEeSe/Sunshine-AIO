# Steam Deck Setup Guide

Complete guide for streaming from your Windows PC to Steam Deck using Sunshine-AIO and Moonlight.

## 🎮 Overview

Streaming to Steam Deck offers several advantages:
- **Portable PC gaming** - Play your Windows library anywhere
- **Better performance** - Leverage your powerful PC GPU
- **Full game compatibility** - Access games not available on Steam Deck
- **Seamless experience** - Controller input works natively

## 🔧 Prerequisites

### On Your PC (Host)
- **Sunshine-AIO installed** and configured
- **Strong network connection** (wired ethernet recommended)
- **Sufficient upload bandwidth** (20+ Mbps for good quality)

### On Your Steam Deck (Client)
- **SteamOS 3.4+** or **Desktop Mode access**
- **Same network** as your PC (WiFi or docked ethernet)
- **Moonlight client** installed

## 📱 Installing Moonlight on Steam Deck

### Method 1: Discovery Store (Recommended)
```bash
# In Desktop Mode
1. Open "Discover" app store
2. Search for "Moonlight"
3. Install "Moonlight Game Streaming"
4. Return to Gaming Mode
```

### Method 2: Flatpak Command Line
```bash
# Open Konsole in Desktop Mode
flatpak install flathub com.moonlight_stream.Moonlight
```

### Method 3: AppImage (Advanced)
```bash
# Download from moonlight-stream.org
wget https://github.com/moonlight-stream/moonlight-qt/releases/latest
# Make executable and run
```

## 🌐 Network Setup

### Optimal Network Configuration

**Wired Connection (Best):**
```
PC → Ethernet → Router → Ethernet → Steam Deck Dock
Latency: ~1-3ms
Bandwidth: Full gigabit available
```

**WiFi Connection (Good):**
```
PC → Ethernet → Router → 5GHz WiFi → Steam Deck
Requirements:
- 5GHz WiFi (not 2.4GHz)
- Strong signal strength (-50 dBm or better)
- Router close to gaming area
```

### Steam Deck Network Optimization

**WiFi Settings:**
1. **Settings → Internet**
2. **Select your 5GHz network**
3. **Advanced → Prefer IPv4**
4. **Set DNS to 1.1.1.1, 8.8.8.8**

**Network Testing:**
```bash
# Test connection to your PC
ping [YOUR_PC_IP]
# Should show <10ms latency

# Test bandwidth
iperf3 -c [YOUR_PC_IP] -t 30
# Should show 50+ Mbps for good streaming
```

## 🎯 Moonlight Configuration

### Initial Setup

**1. Pair with Your PC:**
```
1. Launch Moonlight on Steam Deck
2. Should auto-detect your PC
3. If not found, add manually by IP
4. Enter pairing PIN from Sunshine Web UI
```

**2. Optimal Settings for Steam Deck:**
```
Resolution: 1280×800 (native) or 1920×1080
Frame Rate: 60 FPS
Bitrate: 20-30 Mbps (adjust based on network)
Video Decoder: Hardware acceleration
Audio Configuration: Stereo
```

**3. Advanced Settings:**
```
Game Optimization: On
HDR: Off (Steam Deck LCD) / On (Steam Deck OLED)
Mouse Acceleration: On
Capture System Keys: On
UI Scaling: 125% (for readability)
```

### Steam Deck Specific Optimizations

**Display Settings:**
```json
{
  "resolution": "1280x800",
  "refresh_rate": 60,
  "scaling_mode": "aspect_ratio",
  "hdr_support": "auto"
}
```

**Control Mapping:**
- **Steam Input enabled** for all controllers
- **Steam Deck controls** mapped as Xbox controller
- **Trackpads configured** for mouse input
- **Back buttons** for additional shortcuts

## 🎮 Gaming Mode Integration

### Adding Moonlight as Non-Steam Game

**Method 1: Desktop Mode**
```bash
1. Desktop Mode → Steam Client
2. Games → Add Non-Steam Game
3. Browse to Moonlight location
4. Add to library
5. Configure controller settings
```

**Method 2: Game Mode**
```
1. Steam → Library
2. Add Non-Steam Game
3. Find Moonlight in installed applications
4. Add to library
```

### Steam Input Configuration

**Optimal Controller Template:**
```
Template: "Gamepad with Mouse Trackpad"
Adjustments:
- Right Trackpad: Mouse
- Left Trackpad: D-Pad
- Back Buttons: Alt+Tab, Esc
- Steam Button: Steam Overlay
```

**Per-Game Configurations:**
- **FPS Games:** Mouse + WASD template
- **Strategy Games:** Mouse focus template  
- **Racing Games:** Analog trigger template
- **Retro Games:** D-Pad focused template

## 🖥️ Display & Performance

### Resolution Recommendations

**Native Steam Deck (1280×800):**
- **Best latency** and performance
- **Full screen utilization**
- **Optimal for Steam Deck's display**

**1080p Streaming:**
- **Better quality** on external monitors
- **Higher bandwidth requirements**
- **Good for docked mode**

**Custom Resolutions:**
```
For external 16:9 displays:
- 1920×1080 @ 60Hz
- 1366×768 @ 60Hz (lower bandwidth)

For ultrawide displays:
- 2560×1080 @ 60Hz
- Scale to fit Steam Deck when undocked
```

### Performance Optimization

**On PC (Host):**
```powershell
# Ensure GPU hardware encoding
NVIDIA: NVENC enabled
AMD: AMF enabled
Intel: QuickSync enabled

# Windows optimizations
Disable Xbox Game Bar
Set Power Plan to "High Performance"
Close unnecessary background apps
```

**On Steam Deck (Client):**
```bash
# Set performance profile
sudo steamos-readonly disable
# Edit /etc/default/grub if needed
# Enable maximum performance mode when plugged in
```

### HDR Support

**Steam Deck LCD (Original):**
- **No HDR support** - Keep HDR disabled
- **Standard color gamut** streaming works fine
- **Tone mapping** on PC if needed

**Steam Deck OLED:**
- **HDR support available** 
- **Enable HDR** in both Sunshine and Moonlight
- **Higher brightness** for better HDR experience
- **Color accuracy** improvements over LCD

## 🛠️ Troubleshooting Steam Deck Issues

### Common Problems

**Moonlight Won't Find PC:**
```bash
# Check network connectivity
ping [PC_IP_ADDRESS]

# Manual IP entry
Add computer manually → Enter PC IP

# Firewall check on PC
Windows Firewall → Allow Moonlight/Sunshine
```

**Controller Not Working:**
```
Steam Input Issues:
1. Disable Steam Input for Moonlight
2. Or configure proper controller template
3. Check Steam → Settings → Controller → Desktop Configuration
```

**Performance Issues:**
```
Stuttering/Lag:
1. Lower bitrate to 15-20 Mbps
2. Change resolution to 1280×800
3. Disable HDR if enabled
4. Check WiFi signal strength

Black Screen:
1. Try different video decoder
2. Update Steam Deck system
3. Restart Moonlight application
```

**Audio Problems:**
```
No Audio:
1. Check Steam Deck audio output
2. Set Moonlight to Stereo mode
3. Test with different applications

Audio Delay:
1. Reduce bitrate
2. Use wired connection
3. Close other network applications
```

### Advanced Troubleshooting

**Network Diagnostics:**
```bash
# Check connection quality
mtr -c 10 [PC_IP_ADDRESS]
# Look for packet loss or high latency

# Monitor bandwidth usage
iftop -i wlan0
# Ensure sufficient available bandwidth
```

**Moonlight Logs:**
```bash
# Find Moonlight logs
~/.local/share/Moonlight Game Streaming/
# Check for error messages
```

## 🎯 Optimal Game Configurations

### PC Game Settings

**For Best Streaming Experience:**
```
Resolution: Match streaming resolution
Fullscreen Mode: Borderless Windowed (preferred)
VSync: Off (handled by streaming)
Frame Rate Limit: 60 FPS
Graphics Quality: Medium-High (balance quality/performance)
```

### Game-Specific Recommendations

**Steam Games:**
- **Launch in Big Picture Mode** for controller optimization
- **Enable Steam Input** for better controller support
- **Configure per-game** controller profiles

**Non-Steam Games:**
- **Add to Steam** as non-steam games
- **Configure controls** via Steam Input
- **Test controller** support before streaming

**Competitive Games:**
- **Lower streaming latency** settings
- **Wired network connection** essential
- **Close background applications**
- **Use Game Mode** on Windows PC

## 📊 Performance Monitoring

### Stream Quality Metrics

**Good Performance Indicators:**
```
Latency: <20ms total
Frame drops: <1%
Bitrate: Stable at set value
Network: <50% bandwidth utilization
```

**Monitoring Tools:**
- **Moonlight built-in stats** (Ctrl+Alt+Shift+S)
- **Steam Deck performance overlay**
- **Network monitoring** on router

### Optimization Tips

**Network Optimization:**
```
Router Settings:
- QoS prioritization for streaming
- Gaming mode enabled
- 5GHz channel optimization
- Bandwidth allocation

Steam Deck Settings:
- Performance mode when docked
- Disable auto-suspend during streaming
- Close other applications
```

---

*Having issues? Check the [Troubleshooting Guide](Troubleshooting) or [Steam Deck community forums](https://steamcommunity.com/app/1675200/discussions/) for additional help.*