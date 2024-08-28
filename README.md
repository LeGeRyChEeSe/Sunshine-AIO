<h1 align='center'>Sunshine-AIO</h1>
<p align="center">
<img src="https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/dev-AIO/ressources/sunshine_aio.jpg?raw=true" align="center" height=205 alt="Sunshine-AIO" />
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
<b>This AIO tool branch is under development. Bugs can appear.</b><br>
An all-in-one step-by-step guide to setup Sunshine with all needed tools (Windows x64).<br>


# Table of Contents
- [Sunshine-AIO](#sunshine-aio)
- [Add custom resolutions\\frame rates](#add-custom-resolutionsframe-rates)
	- [Option File](#option-file)
	- [Sunshine Config](#sunshine-config)
- [Build the project](#build-the-project)
	- [Python3 Installation](#python3-installation)
	- [Git Installation](#git-installation)
	- [Setup the repository](#setup-the-repository)
	- [Execute the AIO tool](#execute-the-aio-tool)
	- [Update the repository](#update-the-repository)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [Star History](#star-history)


## Sunshine-AIO

- Download the [Latest Release](https://github.com/LeGeRyChEeSe/Sunshine-AIO/releases/latest) and execute `Sunshine-AIO.exe`.
	
> Playnite and Playnite Watcher are optional, but they are installed by default within the `everything` command.


## Add custom resolutions\frame rates

- You will need to add custom resolutions if your client resolution are [not listed here](https://github.com/itsmikethetech/Virtual-Display-Driver?tab=readme-ov-file#resolutions).

- After you have executed the script once and installed everything:


### Option File

- Open the `"C:\IddSampleDriver\option.txt"` file and add your custom resolutions/frame rates. (E.g. Mobile Phone/TV/Nintendo Switch/Steam Deck)
- Make sure to follow the syntax of the file:

	<b>option.txt:</b>
	```
	RES_WIDTH, RES_HEIGHT, FRAME RATE
	```
- Add as many lines for the same resolution as you want different frame rates.
- For example:

	<b>option.txt:</b>
	```
	(...)
	3120, 1440, 60
	3120, 1440, 90
	3120, 1440, 120
	```

### Sunshine Config

- Open [Sunshine WebUI](https://localhost:47990/config#) and navigate to `Configuration` → `Audio/Video` Tab.
- Scroll down and add your custom resolutions and custom frame rates here.
- Make sure that every resolutions and frame rates are well indicated in the [`"C:\IddSampleDriver\option.txt"`](#option-file) file too.


## Build the Project

- If you want to contribute to the project and add some features or even fix some issues by yourself, or anything else, you can fork this repository (See [Contributing](#contributing)).
- You will need some pre-requisites:

### Python3 Installation

- Download [Latest Python3](https://www.python.org/downloads/) and install it on your computer.
	
- Add python to the Path when asked during the installation.


### Git Installation

- Download [Git for Windows](https://git-scm.com/download/win) and install it on your computer.

	> Dynamic pull of the repository and all the files on your local computer would be advantageous, as you can receive updates when they are available using the `git pull` command.


### Setup the repository

- Go in any location you want to put the folder and open a Windows Terminal at this location. <i>(No matter Powershell or CMD)</i>

Execute these commands :

```batch
git clone --branch dev-AIO https://github.com/LeGeRyChEeSe/Sunshine-AIO.git
cd Sunshine-AIO
py -m venv virtualenv-python-sunshine-aio
virtualenv-python-sunshine-aio\Scripts\pip.exe install -r requirements.txt

```


### Execute the AIO tool

- From the root folder of the repository (Sunshine-AIO), open a terminal and execute this command:

```batch
virtualenv-python-sunshine-aio\Scripts\python.exe src\main.py
```

> To execute the script, an elevated UAC prompt will appear and request `admin permission`.

- To finish the Playnite Watcher configuration, follow the instructions provided in the script.


### Update the repository

In order to receive new updates when I push new features, open a terminal and execute this command in the repository's root folder (Sunshine-AIO):

```git
git pull
```
Stay up-to-date !


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
