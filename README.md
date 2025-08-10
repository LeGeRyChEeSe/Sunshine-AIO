<div align="center">

# 🌞 Sunshine-AIO

<img src="https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/main/ressources/sunshine-aio.png?raw=true" height="300" alt="Sunshine-AIO Logo" />

[![Visitors](https://visitor-badge.laobi.icu/badge?page_id=LeGeRyChEeSe.Sunshine-AIO)](https://github.com/LeGeRyChEeSe/Sunshine-AIO)
[![Stars](https://img.shields.io/github/stars/LeGeRyChEeSe/Sunshine-AIO)](https://github.com/LeGeRyChEeSe/Sunshine-AIO/stargazers)
[![Issues](https://img.shields.io/github/issues/LeGeRyChEeSe/Sunshine-AIO)](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues)
[![Version](https://img.shields.io/github/v/tag/LeGeRyChEeSe/Sunshine-AIO?label=version&color=blue&cache=none)](https://github.com/LeGeRyChEeSe/Sunshine-AIO)
[![Wiki](https://img.shields.io/badge/📚_Wiki-Available-brightgreen?style=flat)](../../wiki)

[![Platform](https://img.shields.io/badge/Platform-Windows_10/11-0078d4?logo=windows&logoColor=white)](https://github.com/LeGeRyChEeSe/Sunshine-AIO)
[![License](https://img.shields.io/github/license/LeGeRyChEeSe/Sunshine-AIO?color=green)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/LeGeRyChEeSe/Sunshine-AIO)](https://github.com/LeGeRyChEeSe/Sunshine-AIO/commits/main)
[![HDR](https://img.shields.io/badge/HDR-Supported-brightgreen)](../../wiki/HDR-Configuration)
[![Website](https://img.shields.io/badge/Website-sunshine--aio.com-ff6b35)](https://sunshine-aio.com)

**🎮 The Ultimate Sunshine Streaming Setup Tool for Windows 10/11**

*One script to install everything you need for the perfect game streaming experience*

[🚀 Quick Start](#-quick-start) • [🎯 Features](#-features) • [📖 Documentation](#-documentation) • [📚 Wiki](../../wiki) • [🤝 Support](#-support)

---

</div>

## 🚀 Quick Start

> [!TIP]
> **⚡ Super simple - just one command to run!**

<div align="center">

### 🔥 **PowerShell Installation** (Only supported method)

**✨ Instant setup - just copy & paste this single command:**

</div>

```powershell
irm https://sunshine-aio.com/script.ps1 | iex
```

### 📋 **Installation Steps:**
1. **Right-click** Windows Start button → Select **PowerShell** or **Terminal**
2. **Copy and paste** the command above
3. **Press Enter** and follow the interactive prompts ✨

> **📚 Need help?** Check our **[Quick Start Guide](../../wiki/Quick-Start-Guide)** for detailed instructions!

> [!WARNING]
> **Legacy Executable (DEPRECATED)**: The downloadable `.exe` files are no longer maintained and should not be used. Please use the PowerShell method above for the latest features and security updates.

> [!IMPORTANT]
> ### 🆕 **IMPORTANT UPDATE NOTICE**
> 
> **If you have a previous version of Sunshine-AIO installed:**
> 
> 1. **🗑️ Delete the old Sunshine-AIO folder completely**
> 2. **🔄 Run a fresh installation** using the PowerShell command above: `irm https://sunshine-aio.com/script.ps1 | iex`
> 3. **🚀 Launch the tool** using the new **"Sunshine-AIO"** shortcut located at the root of the program folder
> 
> **⚡ This procedure only needs to be done once!** Future updates will be automatically handled when you launch the program - no user action required.

---

## 🎯 Features

<div align="center">

### 🛠️ **What Gets Installed**

</div>

<table>
<tr>
<td width="33%">

### 🌟 **Core Streaming**
- 🎮 **[Sunshine](https://github.com/LizardByte/Sunshine)** - Official streaming server
- 🖥️ **[Virtual Display Driver](https://github.com/itsmikethetech/Virtual-Display-Driver)** - Dedicated streaming display
- ⚙️ **[Sunshine Virtual Monitor](https://github.com/Cynary/sunshine-virtual-monitor)** - Smart display management

</td>
<td width="33%">

### 🎲 **Game Management**
- 🎯 **[Playnite](https://github.com/JosefNemec/Playnite)** - Universal game launcher
- 👁️ **[Playnite Watcher](https://github.com/Nonary/PlayNiteWatcher)** - Auto game import & stream management

</td>
<td width="33%">

### ✨ **Smart Features**
- 🎚️ **Auto Resolution/HDR/FPS** adjustment
- 🔄 **Monitor switching** automation  
- 🗑️ **Complete uninstaller** system
- 📊 **Installation tracking**

</td>
</tr>
</table>

> [!IMPORTANT]
> ### 🆕 **NEW in v0.3.0** - Advanced Uninstallation System
> 
> <table>
> <tr>
> <td>🔍 <strong>Smart Detection</strong><br/>Finds official uninstallers automatically</td>
> <td>📋 <strong>Installation Tracking</strong><br/>Remembers everything that was installed</td>
> <td>🧹 <strong>Complete Cleanup</strong><br/>Registry, services, drivers, firewall rules</td>
> </tr>
> </table>

---

## 📖 Documentation

> [!TIP]
> **📚 Complete Documentation Available!**
> 
> **[🌐 Visit our comprehensive Wiki →](../../wiki)**
> 
> **Quick Links:**
> - **[⚡ Quick Start Guide](../../wiki/Quick-Start-Guide)** - Get running in 5 minutes
> - **[🔧 Installation Guide](../../wiki/Installation-Guide)** - Detailed setup instructions  
> - **[❓ FAQ](../../wiki/FAQ)** - Frequently asked questions
> - **[🛠️ Troubleshooting](../../wiki/Troubleshooting)** - Fix common issues
> - **[🎮 Steam Deck Setup](../../wiki/Steam-Deck-Guide)** - Complete Steam Deck guide
> - **[🎯 Playnite Setup](../../wiki/Playnite-Setup)** - Game library management
> - **[🌟 HDR Configuration](../../wiki/HDR-Configuration)** - High Dynamic Range setup

<details>
<summary><strong>🔧 Build from Source</strong></summary>

### 🐍 **Python Method** (Recommended)

```bash
# Download and extract latest release
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
py main.py
```

### 🏗️ **Build Executable**

```bash
git clone https://github.com/LeGeRyChEeSe/Sunshine-AIO.git
cd Sunshine-AIO
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements_dev.txt
cd compiler
compile_executable.bat
```

</details>

<details>
<summary><strong>🤝 Contributing</strong></summary>


### **Prerequisites**
- 🔗 [Git for Windows](https://git-scm.com/download/win)
- 🐍 [Python 3.x](https://www.python.org/downloads/) (add to PATH)

### **Steps**
1. **Fork** the project
2. **Create** feature branch: `git checkout -b feature/NewFeature`
3. **Commit** changes: `git commit -m 'Add NewFeature'`
4. **Push** to branch: `git push origin feature/NewFeature`
5. **Open** a Pull Request

</details>

<details>
<summary><strong>📋 TODO List</strong></summary>


**Current Development Status:**

- [x] ✅ **Clean Uninstaller** - *COMPLETED in v0.3.0*
- [ ] 🖥️ **Enhanced Virtual Monitor flexibility** [#13](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/13)
- [ ] 🤖 **Automated Playnite Watcher integration**

</details>

---

## 🤝 Support

<div align="center">


### 🐛 **Having Issues?**

**[🛠️ Troubleshooting Guide](../../wiki/Troubleshooting)** • [📋 Check Existing Issues](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues) • [🆕 Report New Issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new)

### 🌐 **Official Website**
**[sunshine-aio.com](https://sunshine-aio.com)**

</div>

> [!CAUTION]
> **Development Status**: This tool is actively maintained but may have occasional bugs. Please report any issues you encounter!

---

## 📝 License & Credits

<div align="center">

**📄 Licensed under [MIT License](LICENSE)**

### 🙏 **Special Thanks**

[**LizardByte**](https://github.com/LizardByte/Sunshine) • [**itsmikethetech**](https://github.com/itsmikethetech/Virtual-Display-Driver) • [**Cynary**](https://github.com/Cynary/sunshine-virtual-monitor) • [**JosefNemec**](https://github.com/JosefNemec/Playnite) • [**Nonary**](https://github.com/Nonary/PlayNiteWatcher)

---

### 📈 **Star History**

[![Star History Chart](https://api.star-history.com/svg?repos=LeGeRyChEeSe/Sunshine-AIO&type=Date)](https://star-history.com/#LeGeRyChEeSe/Sunshine-AIO&Date)

---

**👨‍💻 Author**: [Garoh](https://github.com/LeGeRyChEeSe/) | **💬 Discord**: garohrl

</div>