# Frequently Asked Questions (FAQ)

## 🎯 General Questions

### Q: What is Sunshine-AIO and how is it different from regular Sunshine?
**A:** Sunshine-AIO is an all-in-one installer that sets up Sunshine streaming server along with essential companion tools:
- **Regular Sunshine:** Just the streaming server
- **Sunshine-AIO:** Sunshine + Virtual Display Driver + Playnite + optimization tools + automated configuration

It eliminates the manual setup complexity and provides a complete streaming solution out of the box.

### Q: Do I need to install Python or Git before using Sunshine-AIO?
**A:** No! The PowerShell installation script automatically handles everything:
```powershell
irm https://sunshine-aio.com/script.ps1 | iex
```
This will automatically install Python 3.8+, Git, and all required dependencies.

### Q: Do I need to uninstall existing Sunshine before using Sunshine-AIO?
**A:** No, but it's recommended for a clean setup. The installation script can detect and integrate existing installations, or you can use the built-in uninstaller after installation.

### Q: Which Windows versions are supported?
**A:** 
- ✅ **Windows 10** (version 1903+)
- ✅ **Windows 11** (all versions)
- ❌ Windows 7/8 (not supported)
- ❌ Windows Server editions (untested)

## 🖥️ Virtual Display Questions

### Q: Why do I need a Virtual Display Driver?
**A:** Virtual displays allow you to:
- Stream without affecting your main monitor
- Create custom resolutions for different clients
- Stream while your physical display is off/disconnected
- Support multiple simultaneous clients

### Q: Can I use Sunshine-AIO without Virtual Display Driver?
**A:** Yes, but with limitations:
- Your main monitor will mirror what the client sees
- Resolution changes will affect your local display
- Can't stream while display is locked/off

### Q: Which Virtual Display Driver does Sunshine-AIO use?
**A:** Sunshine-AIO uses **IDD Sample Driver** (Microsoft's reference implementation). It's:
- ✅ Free and open-source
- ✅ Officially supported by Microsoft
- ✅ Compatible with most systems
- ✅ Supports HDR

## 🎮 Gaming & Streaming Questions

### Q: Can I stream games from different launchers (Steam, Epic, etc.)?
**A:** Yes! Sunshine-AIO supports all game launchers:
- **Steam Big Picture** (recommended for best experience)
- **Epic Games Launcher**
- **Xbox Game Pass**
- **GOG Galaxy**
- **Individual game executables**
- **Playnite** (unified game library)

### Q: What's the difference between Playnite and Steam Big Picture?
**A:**
| Feature | Playnite | Steam Big Picture |
|---------|----------|-------------------|
| Game Sources | All launchers | Steam only |
| Interface | Customizable | Fixed Steam UI |
| Controller Support | Universal | Excellent |
| Streaming Optimization | Good | Excellent |
| **Recommendation** | Use both! | Steam games only |

### Q: Can I stream to multiple devices simultaneously?
**A:** 
- **Sunshine limitation:** One active stream at a time
- **Workaround:** Use multiple virtual displays with different Sunshine instances (advanced setup)
- **Alternative:** Use Parsec for multi-user scenarios

### Q: Does Sunshine-AIO support HDR?
**A:** Yes, with requirements:
- **Host:** HDR-capable GPU and display
- **Client:** HDR-capable display
- **Network:** Sufficient bandwidth (40+ Mbps recommended)
- **Configuration:** HDR enabled in both Sunshine and client

## 🔧 Technical Questions

### Q: What are the system requirements?
**A:**
**Minimum:**
- Windows 10 1903+ or Windows 11
- DirectX 11 compatible GPU
- 4GB RAM
- Administrator privileges

**Recommended:**
- Modern NVIDIA/AMD GPU with hardware encoding
- 8GB+ RAM
- Wired network connection
- SSD storage

### Q: Why does installation require Administrator privileges?
**A:** Administrator rights are needed for:
- Installing Windows services (SunshineService)
- Installing Virtual Display Driver
- Modifying system display settings
- Creating firewall exceptions

### Q: Can I run Sunshine-AIO on a virtual machine?
**A:** Limited support:
- **VMware:** Possible with GPU passthrough
- **VirtualBox:** Not recommended (no GPU acceleration)
- **Hyper-V:** Possible with RemoteFX (deprecated)
- **Best practice:** Use physical hardware for optimal performance

## 🌐 Network & Connection Questions

### Q: What ports does Sunshine-AIO use?
**A:**
- **47989** - Main streaming port (TCP/UDP)
- **47990** - Web UI (HTTPS)
- **48010** - RTSP port (TCP)
- **Auto-discovery:** mDNS/Bonjour

### Q: Can I stream over the internet (WAN)?
**A:** Yes, with setup:
1. **Port forwarding:** Forward port 47989 on your router
2. **Dynamic DNS:** Use service like No-IP if you don't have static IP
3. **Security:** Enable authentication in Sunshine
4. **Bandwidth:** Ensure sufficient upload speed (20+ Mbps)

### Q: Why is streaming laggy or pixelated?
**A:** Common causes and solutions:
- **Network:** Use wired connection when possible
- **Bitrate:** Adjust in Sunshine settings (lower for slow networks)
- **Encoder:** Use hardware encoding (NVENC/AMF)
- **Resolution:** Match client native resolution
- **FPS:** Don't exceed client display refresh rate

## 🛠️ Troubleshooting Questions

### Q: Installation fails with "execution of scripts is disabled"
**A:** PowerShell execution policy issue:
```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: Virtual display doesn't appear after installation
**A:** Try these steps:
1. **Restart Windows** (required for some systems)
2. **Check Device Manager** for "IDD HDR" under Display adapters
3. **Run VDD Control manually:**
   ```
   tools\VDD Control\VDD Control.exe
   Click "Install Driver"
   ```

### Q: Moonlight shows "Computer is unreachable"
**A:** Network connectivity issue:
1. **Same network:** Ensure both devices on same WiFi/LAN
2. **Firewall:** Allow Sunshine through Windows Firewall
3. **Manual IP:** Try connecting by IP address instead of auto-discovery
4. **Antivirus:** Temporarily disable to test

### Q: Games launch but I see black screen
**A:** Display capture issue:
1. **Run game in windowed mode** first
2. **Check game's graphics API** (prefer DirectX over Vulkan/OpenGL)
3. **Update GPU drivers**
4. **Try different capture method** in Sunshine settings

## 📱 Client Questions

### Q: Which Moonlight client should I use?
**A:** 
- **Windows/Mac/Linux:** Official Moonlight PC client
- **Android/iOS:** Official Moonlight mobile apps  
- **Steam Deck:** Official Moonlight from Discover store
- **Smart TV:** Check if your TV supports Moonlight apps
- **Raspberry Pi:** Official Moonlight embedded

### Q: Can I use other streaming clients besides Moonlight?
**A:** Moonlight is the only compatible client. Sunshine uses NVIDIA GameStream protocol, which only Moonlight supports. Alternatives like:
- **Chrome Remote Desktop:** Different protocol
- **Parsec:** Different service entirely
- **Steam Link:** Steam-specific streaming

## 🔄 Updates & Maintenance

### Q: How do I update Sunshine-AIO?
**A:** 
1. **Fastest method (Recommended):** 
   ```powershell
   irm https://sunshine-aio.com/script.ps1 | iex
   ```
   When prompted, provide your existing Sunshine-AIO installation path and the tool will automatically update.

2. **Manual method:**
   - Check current version: Look at bottom of main menu
   - Download latest release: GitHub releases page
   - Backup settings: Export Sunshine configuration
   - Clean install recommended: Uninstall old version first

### Q: How do I completely uninstall Sunshine-AIO?
**A:** Use the built-in uninstaller:
```python
python src/main.py
# Select "Uninstall all components"
```

This removes:
- All installed applications
- Virtual Display Driver
- Services and registry entries
- Created files and folders

### Q: Where are configuration files stored?
**A:**
- **Sunshine config:** `C:\ProgramData\Sunshine\`
- **Installation tracker:** `src\misc\variables\installation_tracker.json`
- **Logs:** `C:\ProgramData\Sunshine\sunshine.log`
- **App configs:** Sunshine Web UI → Applications

## 🤝 Community & Support

### Q: Where can I get help if I'm still stuck?
**A:**
1. **Check this Wiki** - Most issues covered here
2. **Search GitHub Issues** - Someone might have same problem
3. **Create new issue** - Include system specs and logs
4. **Join community discussions** - Help other users too!

### Q: Can I contribute to Sunshine-AIO?
**A:** Absolutely! We welcome:
- **Bug reports** with detailed reproduction steps
- **Feature requests** for new functionality
- **Code contributions** via pull requests
- **Documentation improvements**
- **Translations** for other languages

### Q: Is Sunshine-AIO free?
**A:** Yes, completely free and open-source under MIT license. No premium features, no ads, no data collection.

---

*Don't see your question here? Check the [Troubleshooting Guide](Troubleshooting) or [create an issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new)!*