<h1 align='center'>Sunshine-AIO</h1>
<p align="center">
<img src="https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/main/ressources/sunshine_aio.jpg?raw=true" align="center" height=350 alt="Sunshine-AIO" />
</p>
<p align="center">
<img src='https://visitor-badge.laobi.icu/badge?page_id=LeGeRyChEeSe.Sunshine-AIO', alt='Visitors'/>
<a href="https://github.com/LeGeRyChEeSe/Sunshine-AIO/stargazers">
<img src="https://img.shields.io/github/stars/LeGeRyChEeSe/Sunshine-AIO" alt="Stars"/>
</a>
<a href="https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues">
<img src="https://img.shields.io/github/issues/LeGeRyChEeSe/Sunshine-AIO" alt="Issues"/>
</a>

<p align="center">
An all-in-one tool to setup Sunshine with all needed tools (Windows 10/11).<br>
It includes: (Official) Sunshine Installation, Virtual Display Driver, Sunshine Virtual Monitor, Playnite and Playnite Watcher.
</p>

> [!WARNING]
> :construction: <b>This Tool is under development. Bugs can appear.</b> :construction:

<h2 align='center'>Current Features</h2>

- [x] <b>(Official) [Sunshine](https://github.com/LizardByte/Sunshine) Installation</b>
- [x] <b>[Virtual Display Driver](https://github.com/itsmikethetech/Virtual-Display-Driver)</b>
    - A dedicated display for your game stream will be created.

> [!NOTE]
> The `"C:\IddSampleDriver\option.txt"` file is now **automatically** managed by the **Sunshine Virtual Monitor** tool.
>
> You don't need to manually copy this file anymore.
- [x] <b>[Sunshine Virtual Monitor](https://github.com/Cynary/sunshine-virtual-monitor)</b>
    - An <b>automated</b> script to:
        1. Automatically adjust the <b>Resolution</b>, <b>HDR</b>, and <b>Frame Rate</b> of the Virtual Display based on Moonlight client settings.
        2. <b>Deactivate</b> all your physical monitors and <b>enable</b> the dedicated Virtual Display to stream your games.
- [x] <b>[Playnite](https://github.com/JosefNemec/Playnite)</b>
    - A <b>Universal Launcher</b> to launch all your favorites games from one place.
- [x] <b>[Playnite Watcher](https://github.com/Nonary/PlayNiteWatcher)</b>
    - An <b>automated</b> script to:
        1. <b>Import</b> all your favorite games into Sunshine effortlessly.
        2. <b>Gracefully</b> stop the stream when you close a game.


# Table of Contents
- [Sunshine-AIO](#sunshine-aio)
- [Troubleshooting](#troubleshooting)
- [Build The Executable](#build-the-executable)
- [Contributing](#contributing)
	- [Git Installation](#git-installation)
	- [Python3 Installation](#python3-installation)
- [TODO list](#todo-list)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Star History](#star-history)


## Sunshine-AIO

- Download the [Latest Release](https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases/latest) and execute `Sunshine-AIO.exe`.

> [!WARNING]
> The file might be flagged as Trojan/Malware, but it's a false positive. (It is due to **Nuitka** build)
>
> To prevent the file being deleted by your anti-virus, make sure to temporarily disable your anti-virus, or add an exception to the folder you want to download the file.

> [!NOTE]	
> Playnite and Playnite Watcher are optional, but they are installed by default within the `everything` command.


## Troubleshooting

> [!CAUTION]
> Please keep in mind this AIO tool is still in development and you may encounter bugs or issues when using it.
>
> Some features mentioned in the first lines of this readme aren't yet implemented such as *clean uninstaller* feature.
>
> I'm working on it but it could take some times to implement.

Please check the [opened issues](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues) before opening a new issue.

Make sure to configure your Moonlight client to connect to Sunshine and enjoy optimized streaming! 🌞


## Build The Executable

- If you are afraid of the potential viruses in the `Sunshine-AIO.exe` (I 100% certify there are no viruses), you can build the executable yourself from this repo.

- Clone the repo with the `git clone https://github.com/LeGeRyChEeSe/Sunshine-AIO.git` command somewhere in a safe location and execute these commands:

> [!WARNING]
> Before trying to build the executable, make sure you have [Python](#python3-installation) and [Git](#git-installation) installed.

```batch
cd Sunshine-AIO
py -m venv venv
venv\Script\activate
pip install -r requirements.txt
cd compiler
compile_executable.bat

```

- The executable should then appear in the `produced` folder next to the `compile_executable.bat` file.


## Contributing

Any contributions you make are **greatly appreciated**.

1. Fork the Project.
2. Create your Feature Branch. (`git checkout -b feature/NewFeature`)
3. Commit your Changes. (`git commit -m 'Add some NewFeature'`)
4. Push to the Branch. (`git push origin feature/NewFeature`)
5. Open a Pull Request.

<i>Thanks to every [contributors](https://github.com/LeGeRyChEeSe/Sunshine-AIO/graphs/contributors) who have contributed in this project.</i>

- You will need some pre-requisites:


### Git Installation

- Download [Git for Windows](https://git-scm.com/download/win) and install it on your computer.


### Python3 Installation

- Download [Latest Python3](https://www.python.org/downloads/) and install it on your computer.

>[!IMPORTANT]
> Add python to the Path when asked during the installation.

- Install all the packages required to build the project:
```batch
cd Sunshine-AIO
py -m venv venv
venv\Script\activate
pip install -r requirements.txt

```


## TODO list

- [ ] *Have more flexibility with Sunshine Virtual Monitor to manage different setups.* [#13](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/13)
- [ ] *Automate the Playnite Watcher script/Add an option to execute it from the AIO tool.*
- [ ] *Clean Uninstaller* [#12](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/12)


## License

Distributed under the MIT License. See [LICENSE](https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/main/LICENSE) for more information.


## Acknowledgements

Shoutout to <b>LizardByte</b> for the Sunshine repo: https://github.com/LizardByte/Sunshine

Shoutout to <b>itsmikethetech</b> for the Virtual Display Driver repo: https://github.com/itsmikethetech/Virtual-Display-Driver

Thanks to <b>Cynary</b> for the Sunshine Virtual Monitor scripts: https://github.com/Cynary/sunshine-virtual-monitor

Shoutout to <b>JosefNemec</b> for Playnite: https://github.com/JosefNemec/Playnite

Shoutout to <b>Nonary</b> for the PlayNiteWatcher script: https://github.com/Nonary/PlayNiteWatcher


## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=LeGeRyChEeSe/Sunshine-AIO&type=Date)](https://star-history.com/#LeGeRyChEeSe/Sunshine-AIO&Date)

----

Author/Maintainer: [Garoh](https://github.com/LeGeRyChEeSe/) | Discord: garohrl
