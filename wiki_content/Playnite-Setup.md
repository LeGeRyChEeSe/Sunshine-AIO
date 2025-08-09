# Playnite Setup Guide

Complete guide for configuring Playnite with Sunshine-AIO for the ultimate gaming library streaming experience.

## 🎮 Overview

Playnite is a unified game library manager that consolidates games from all platforms into a single interface, perfect for streaming. It supports:
- **Steam, Epic Games Store, GOG, Xbox Game Pass**
- **Origin, Uplay, Battle.net, Itch.io**
- **Emulators and standalone games**
- **Custom categories and metadata**

## 📋 Prerequisites

- **Sunshine-AIO installed** with Playnite component selected
- **Game launchers** already installed (Steam, Epic, etc.)
- **Controllers configured** for couch gaming
- **Moonlight client** set up on streaming device

## 🚀 Initial Playnite Configuration

### First Launch Setup

**1. Language and Theme:**
```
Language: English (or your preference)
Theme: Fullscreen theme (recommended for streaming)
Database Location: Default (C:\Users\[user]\AppData\Roaming\Playnite)
```

**2. Library Integration:**
```
✅ Steam - Import Steam games
✅ Epic Games Store - Import Epic games  
✅ GOG - Import GOG games
✅ Xbox Game Pass - Import Game Pass titles
✅ Origin - Import Origin games
✅ Uplay - Import Ubisoft games
⬜ Emulators - Configure later if needed
```

**3. Metadata Sources:**
```
✅ IGDB - Primary game database
✅ SteamGridDB - Game artwork
✅ YouTube - Game trailers
✅ HowLongToBeat - Game completion times
```

### Fullscreen Mode Optimization

**Settings for Streaming:**
```
Interface → Fullscreen:
- Theme: Modern or Console-style
- Top Panel: Show only essential items
- Game Details: Minimal information
- Background: Dynamic game artwork
```

**Controller Navigation:**
```
Input → Fullscreen:
- Guide Button: Open game menu
- Menu Button: Playnite main menu
- View Button: Filter options
- Shoulder Buttons: Quick navigation
```

## 🎯 Sunshine Integration

### Adding Playnite to Sunshine

**Sunshine App Configuration:**
```json
{
  "name": "Playnite Fullscreen",
  "cmd": "C:\\Program Files\\Playnite\\Playnite.FullscreenApp.exe",
  "working-dir": "C:\\Program Files\\Playnite",
  "prep-cmd": [],
  "detached": []
}
```

**Alternative Desktop Mode:**
```json
{
  "name": "Playnite Desktop",
  "cmd": "C:\\Program Files\\Playnite\\Playnite.DesktopApp.exe",
  "working-dir": "C:\\Program Files\\Playnite",
  "prep-cmd": [],
  "detached": []
}
```

### Prep Commands (Optional)

**For Better Streaming Experience:**
```json
{
  "prep-cmd": [
    "taskkill /f /im Discord.exe /t",
    "taskkill /f /im Spotify.exe /t",
    "net stop \"Windows Search\""
  ]
}
```

**Display Optimization:**
```json
{
  "prep-cmd": [
    "powershell.exe -file optimize_display.ps1"
  ]
}
```

## 🛠️ Playnite Watcher Configuration

### What is Playnite Watcher?

Playnite Watcher enhances streaming by:
- **Monitoring game sessions** for better statistics
- **Automatic launcher management**
- **Stream-specific optimizations**
- **Performance monitoring**

### Installation Verification

**Check if Installed:**
```batch
dir "tools\PlayniteWatcher"
# Should show PlayniteWatcher.exe and configuration files
```

**Manual Setup (if needed):**
1. **Download** from tools folder
2. **Extract** to Playnite Watcher directory
3. **Run** PlayniteWatcher.exe as Administrator
4. **Configure** monitoring settings

### Watcher Configuration

**Basic Settings:**
```json
{
  "monitor_playnite": true,
  "log_game_sessions": true,
  "optimize_for_streaming": true,
  "auto_close_launchers": false
}
```

## 🎨 Theme and UI Customization

### Recommended Themes

**For Streaming (Fullscreen):**
- **Modern** - Clean, controller-friendly
- **Console** - Console-like experience
- **Stardust** - Visually appealing
- **Night** - Dark theme for better contrast

**Theme Installation:**
```
1. Playnite → Add-ons → Browse
2. Search for theme name
3. Download and Install
4. Settings → Appearance → Theme
```

### Layout Optimization

**Fullscreen Layout:**
```
Main View:
- Grid View: 4x3 or 3x2 for TV viewing
- Game Details: Minimal overlay
- Filters: Quick access sidebar
- Search: Easily accessible

Game View:
- Large cover art
- Essential information only
- Quick action buttons
- Controller-friendly navigation
```

**Custom Fields:**
```
Add custom fields for streaming:
- Streaming Quality: Excellent/Good/Poor
- Controller Support: Full/Partial/None
- Stream Notes: Special requirements
- Last Streamed: Tracking usage
```

## 🎯 Game Library Organization

### Categories for Streaming

**Create these categories:**
```
🎮 Stream Favorites - Best streaming games
🏆 Competitive - Low-latency games
🎬 Story Games - Single-player experiences
👥 Multiplayer - Online gaming
🕹️ Local Co-op - Couch gaming
📱 Controller Only - No KB/M needed
⚡ Quick Play - Short gaming sessions
```

**Auto-categorization Rules:**
```
Steam Games with "Controller" tag → Controller Only
Games with multiplayer → Multiplayer
Games under 2 hours completion → Quick Play
```

### Metadata Optimization

**Essential Metadata:**
- **Cover Art** - High resolution for streaming
- **Background Images** - Fullscreen themes
- **Game Descriptions** - Help with selection
- **Tags** - For filtering and organization
- **Play Time** - Track usage

**Custom Scripts:**
```javascript
// Auto-tag games for streaming compatibility
if (game.platform == "Steam" && game.features.includes("Full Controller Support")) {
    game.tags.push("Stream Ready");
}
```

## 🎮 Controller Configuration

### Steam Input Integration

**For Steam Games:**
```
1. Enable Steam Input in Steam settings
2. Configure controller in Steam Big Picture
3. Test in Playnite → should work automatically
4. Create custom configurations per game type
```

**Controller Templates:**
- **Action Games** - Standard gamepad
- **FPS Games** - Gyro aiming enabled
- **Strategy Games** - Mouse emulation
- **Racing Games** - Analog triggers optimized

### Non-Steam Games

**Controller Setup:**
```
1. Add games to Steam as non-Steam games
2. Configure Steam Input for each game
3. Launch through Steam from Playnite
4. Or use native controller support if available
```

## 📊 Performance Optimization

### Playnite Settings for Streaming

**Performance Options:**
```
Advanced → Performance:
- Disable animations: For lower latency
- Reduce metadata loading: Faster startup
- Cache game images: Smoother browsing
- Minimize background tasks: More resources for games
```

**Memory Management:**
```
Advanced → Application:
- Close Playnite when game starts: Optional
- Minimize to tray: Saves resources
- Disable fullscreen optimizations: Windows 10/11
```

### Database Optimization

**Large Libraries:**
```
Tools → Database:
- Regular database cleanup
- Remove unused metadata
- Optimize image sizes
- Archive old game data
```

## 🛠️ Troubleshooting Common Issues

### Playnite Won't Launch via Streaming

**Issue:** Playnite opens locally but not via Moonlight

**Solutions:**
1. **Check Sunshine app path:**
   ```
   Verify: C:\Program Files\Playnite\Playnite.FullscreenApp.exe
   Test locally: Run the exact command
   ```

2. **Disable Global Prep Commands:**
   - Sunshine Web UI → Configuration
   - Uncheck "Global Prep Commands"
   - Test Playnite streaming

3. **Run as Different User:**
   ```json
   {
     "cmd": "runas /user:Administrator \"C:\\Program Files\\Playnite\\Playnite.FullscreenApp.exe\""
   }
   ```

### Controller Not Working in Playnite

**Steam Input Issues:**
1. **Disable Steam Input for Playnite:**
   - Steam → Settings → Controller
   - Desktop Configuration → Disable for Playnite

2. **Configure Playnite Controller:**
   - Playnite → Settings → Input
   - Configure controller manually
   - Test each button mapping

### Games Not Launching from Playnite

**Launcher Issues:**
1. **Update game launchers** (Steam, Epic, etc.)
2. **Verify game installation** paths in Playnite
3. **Check launcher login** status
4. **Run Playnite as Administrator**

### Performance Issues During Streaming

**Optimization Steps:**
1. **Close unnecessary launchers**
2. **Disable Playnite animations**
3. **Reduce streaming bitrate**
4. **Use wired network connection**

## 🎯 Advanced Configuration

### Custom Scripts

**Useful Playnite Scripts:**
```javascript
// Auto-close launchers after game ends
function onGameStopped(game) {
    if (game.platform == "Steam") {
        // Keep Steam running
        return;
    }
    // Close other launchers
    closeProcess(game.platform + ".exe");
}
```

**Streaming Optimization Script:**
```powershell
# optimize_for_streaming.ps1
Stop-Process -Name "Discord" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "Spotify" -Force -ErrorAction SilentlyContinue
Set-Process -Name "Playnite.FullscreenApp" -ProcessorAffinity 0xF
```

### Extensions and Add-ons

**Recommended Extensions:**
- **Extra Metadata Tools** - Enhanced game info
- **Duplicate Hider** - Clean up duplicates
- **How Long To Beat** - Game length info
- **Success Story** - Achievement tracking
- **Game Activity** - Detailed play tracking

**For Streaming:**
- **Fullscreen Helper** - Better fullscreen mode
- **Controller Support** - Enhanced controller features
- **Night Theme** - Better for dark rooms

## 📱 Mobile and Portable Integration

### Steam Deck Specific

**Playnite on Steam Deck:**
```
1. Add Playnite as non-Steam game
2. Configure Steam Input template
3. Use Desktop mode for setup
4. Stream from Windows PC with Playnite
```

**Recommended Settings:**
- **Resolution:** 1280x800 for Steam Deck native
- **Interface:** Large text and buttons
- **Controller:** Steam Deck native support

### Smartphone/Tablet Streaming

**Moonlight Mobile + Playnite:**
- **Touch controls:** Enable in Moonlight
- **On-screen keyboard:** For search/navigation
- **Portrait mode:** Some games support it
- **Virtual controller:** For non-controller games

---

*For troubleshooting specific games or advanced configurations, see the [Troubleshooting Guide](Troubleshooting) or [Gaming Setup FAQ](FAQ#gaming--streaming-questions).*