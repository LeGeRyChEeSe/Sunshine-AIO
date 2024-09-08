# Changelog


## v0.2.0-dev (08 September 2024)
- :partying_face: **Big Update !** The AIO tool get stronger with a new cool feature. See below.
- Bugs may appear. Please [open an issue](https://github.com/LeGeRyChEeSe/Sunshine-AIO/issues/new) if you have one.
- Tool still under development.

### Added
- Compiler script for paranoïac users. (The release contains no viruses but it's flagged as is in VirusTotal)
- :partying_face: **New awesome feature:** Full automatic resolution/frame rate settings from Moonlight to Virtual Display Driver without Human Intervention needed.

### Changed
- No more need to manually add resolutions and frame rates in the `option.txt` file.
    - It implies that no `option.txt` will be created at installation with this tool. It will create it and add specific resolutions/frame rates only when you start the stream.
    - The `option.txt` will now only contain **your** resolutions/frame rates.
- Removed the useless parameter `VDD_NAME` in `do_cmd` and `undo_cmd` command preps as it is now **fully auto** retrieved by the Sunshine Virtual Monitor script.
- Sunshine Virtual Monitor repository switched back to the original one.
- No more check for execution policy and no more changes for global policies. It uses a local policy that scope only the current process.

### Fixed
- A more robust way to work with powershell commands should have fixed some path issues. (Didn't tested all the possibilities)
- HDR is now fully working again! (I broke it up on a previous release and didn't realize then)
- Small issues are also fixed with this release.
