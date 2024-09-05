<h1 align='center'>Sunshine-AIO</h1>
<p align="center">
<img src="https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/dev-AIO/ressources/sunshine_aio.jpg?raw=true" align="center" height=350 alt="Sunshine-AIO" />
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
It includes: Sunshine, Virtual Display Driver, Sunshine Virtual Monitor, Playnite and Playnite Watcher.
</p>

> [!WARNING]
> :construction:<b>This Branch is under development. Bugs can appear.</b>:construction:

<h2 align='center'>What is the purpose of installing all of these tools?</h2>

<b>There are several reasons:</b>

- A dedicated display for your game stream will be created by the <b>Virtual Display Driver</b>.

- <b>Sunshine Virtual Monitor</b> will deactivate all your physical monitors and enable the Virtual Display to stream your games.

> [!NOTE]
> It will <b>automatically</b> adjust the resolution, quality, HDR option, and frame rate of the Virtual Display based on Moonlight client settings.

- <b>Playnite</b> will allow you to gather all your games from any platform in one launcher for your convenience.

- <b>Playnite Watcher</b> stop the stream when the game is closed. (Sunshine does not support it natively)

>[!NOTE]
> It will import all your games into Sunshine effortlessly.

# Table of Contents
- [Sunshine-AIO](#sunshine-aio)
- [Add Custom Resolutions\\Frame Rates](#add-custom-resolutionsframe-rates)
	- [Option File](#option-file)
	- [Sunshine Config](#sunshine-config)
- [Build the project](#build-the-project)
	- [Python3 Installation](#python3-installation)
	- [Git Installation](#git-installation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Star History](#star-history)


## Sunshine-AIO

- Download the [Latest Release](https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases/latest) and execute `Sunshine-AIO.exe`.

> [!NOTE]	
> Playnite and Playnite Watcher are optional, but they are installed by default within the `everything` command.


## Add Custom Resolutions\Frame Rates

- You will need to add custom resolutions if your client resolutions are [not listed here](https://github.com/itsmikethetech/Virtual-Display-Driver?tab=readme-ov-file#resolutions).

- After you have executed the script once and installed everything:


### Option File

- Open the `"C:\IddSampleDriver\option.txt"` file and add your custom Resolutions/Frame Rates.

> [!TIP]
> Open the `option.txt` file via Sunshine-AIO from `7. Extra` → `5. Edit Custom Resolutions/Frame Rates (option.txt)`

> [!IMPORTANT]
> Make sure to follow the syntax of the file:
>
>	<b>option.txt:</b>
>	```
>	RES_WIDTH, RES_HEIGHT, FRAME_RATE
>	```
- Add a line for each frame rate wanted for one resolution.
- For example:

	<b>option.txt:</b>
	```
	(...)
	3120, 1440, 60
	3120, 1440, 90
	3120, 1440, 120
	```

> [!WARNING]
> Make sure the Virtual Display Driver is <b>disabled</b>.


### Sunshine Config

- Open [Sunshine WebUI](https://localhost:47990/config#) and navigate to `Configuration` → `Audio/Video` Tab.

> [!TIP]
> Open Sunshine Config via Sunshine-AIO from `7. Extra` → `6. Open Sunshine Settings`

- Scroll down and add your custom resolutions and custom frame rates here.
- Make sure that every resolutions and frame rates are well indicated in the [`"C:\IddSampleDriver\option.txt"`](#option-file) file too.


## Build the Project

- If you want to contribute to the project and add some features or even fix some issues by yourself, or anything else, you can fork this repository (See [Contributing](#contributing)).
- You will need some pre-requisites:


### Python3 Installation

- Download [Latest Python3](https://www.python.org/downloads/) and install it on your computer.

>[!IMPORTANT]
> Add python to the Path when asked during the installation.


### Git Installation

- Download [Git for Windows](https://git-scm.com/download/win) and install it on your computer.

> [!NOTE]
> Dynamic pull of the repository and all the files on your local computer would be advantageous, as you can receive updates when they are available using the `git pull` command.


## Troubleshooting

Please keep in mind this AIO tool is still in development and you may encounter bugs or issues when using it.

I may have also forgotten to implement some functions due to the fact that the script is at its very first version. I didn’t test all the options that the script provides, because I wanted to provide a first version quickly so as to have your feedback and allow to progress faster than on my own. It works for me, but I suspect that it may not work at first for some of you.

Opening an issue at https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new/choose is encouraged to receive initial help and improve the script.

Feel free to ask me any questions, so that I can one day provide the final version of the script to everyone.

Don't forget to configure your Moonlight client to connect to Sunshine and enjoy optimized streaming :)


## Contributing

Any contributions you make are **greatly appreciated**.

1. Fork the Project.
2. Create your Feature Branch. (`git checkout -b feature/NewFeature`)
3. Commit your Changes. (`git commit -m 'Add some NewFeature'`)
4. Push to the Branch. (`git push origin feature/NewFeature`)
5. Open a Pull Request.


<i>Thanks to every [contributors](https://github.com/LeGeRyChEeSe/Sunshine-AIO/graphs/contributors) who have contributed in this project.</i>


## License

Distributed under the MIT License. See [LICENSE](https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/dev-AIO/LICENSE) for more information.


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
