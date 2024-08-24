<h1 align='center'>Sunshine-AIO</h1>
<p align="center">
<img src="https://github.com/LeGeRyChEeSe/Sunshine-AIO/blob/main/sunshine_aio.jpg?raw=true" align="center" height=205 alt="Sunshine-AIO" />
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

## Python3 Installation

- Download [Latest Python3](https://www.python.org/downloads/) and install it on your computer.
	
- Add python to the Path when asked during the installation.


## Git Installation

- Download [Git for Windows](https://git-scm.com/download/win) and install it on your computer.

	> Dynamic pull of the repository and all the files on your local computer would be advantageous, as you can receive updates when they are available using the `git pull` command.

## Setup the repository

- Go in any location you want to put the folder in and open a terminal at this location.

Execute this command :

```batch
git clone --branch dev-AIO https://github.com/LeGeRyChEeSe/Sunshine-AIO.git
cd Sunshine-AIO
py -m venv virtualenv-python-sunshine-aio
virtualenv-python-sunshine-aio\Scripts\activate.bat
pip install -r requirements.txt
```

### Execute the AIO tool

- From the root folder of the repository (Sunshine-AIO), open a terminal and execute this command:

```batch
virtualenv-python-sunshine-aio\Scripts\python.exe src\main.py
```

> To execute the script, an elevated UAC prompt will appear and request `admin permission`.

- To finish the Playnite Watcher configuration, follow the instructions provided in the script.

## Update the repository

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

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewFeature`)
3. Commit your Changes (`git commit -m 'Add some NewFeature'`)
4. Push to the Branch (`git push origin feature/NewFeature`)
5. Open a Pull Request


<i>Thanks to every [contributors](https://github.com/LeGeRyChEeSe/Sunshine-AIO/graphs/contributors) who have contributed in this project.</i>

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