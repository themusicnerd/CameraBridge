# Installation

## Requirements

| Package | Processor | Build and test system |
|---|---|---|
| Windows | x64 | Windows Server 2022 runner |
| Linux | x64 | Ubuntu 22.04 runner; GNU libc 2.35 or later |
| macOS Intel | x64 | macOS 15 runner |
| macOS Apple silicon | arm64 | macOS 15 runner |

The release workflow tests each package on its build system.
It does not establish compatibility with every system version.
Linux systems that use musl are not release targets.
The macOS packages do not have an Apple Developer ID signature or notarization.
The Windows package does not have a publisher signature.
Follow your organization's software approval procedure if the system blocks the program.

Install Ross DashBoard separately to use the native grid panels.
Use the web interface without DashBoard if only administration is required.

## Install a package

1. Download the applicable archive and its `.sha256` file from the private GitHub release.
2. Check the archive hash against the `.sha256` file.
3. Extract the complete archive to a user-owned directory.
4. Open CameraBridge.exe on Windows, CameraBridge.app on macOS, or CameraBridge on Linux.
5. Create an administrator account in the control panel.
6. Select **Start**.
7. Select **Open setup page**.

The desktop starts in simulator mode.
Use the [desktop procedure](desktop.md) to set its port, configuration and startup options.
Linux requires a graphical desktop with a tray area for tray operation.
If no tray is available, closing the control panel stops the service.
Use CameraBridge-cli for a terminal or headless host.

Use `.\CameraBridge-cli.exe` for terminal commands on Windows.
Use `./CameraBridge-cli` for terminal commands on Linux and macOS.
Keep the `_internal` directory beside the executable.
Do not move the executable alone.

Windows hash command:

```powershell
Get-FileHash .\CameraBridge-0.2.0rc1-windows-x64.zip -Algorithm SHA256
```

Linux hash command:

```sh
sha256sum CameraBridge-0.2.0rc1-linux-x64.tar.gz
```

macOS hash command:

```sh
shasum -a 256 CameraBridge-0.2.0rc1-macos-arm64.tar.gz
```

Select the Intel archive name if the Mac has an Intel processor.

## Application data

| Mode | Default data directory |
|---|---|
| Windows package | `%LOCALAPPDATA%/CameraBridge` |
| Linux package | `$XDG_DATA_HOME/camerabridge`, or `~/.local/share/camerabridge` |
| macOS package | `~/Library/Application Support/CameraBridge` |
| Source | `runtime` in the source directory |

Use `--storage PATH` to select a different directory.
The directory contains accounts, shot names, snapshots, desktop settings and pending configuration files.
Do not copy account files into a release archive.

## Export native panels

1. Run `CameraBridge-cli panels --output ./panels`.
2. Open the exported grid files in DashBoard.
3. Keep the exported assets directory with the grid files.

Run the export command again after you move the panel directory.
It sets the local manufacturer image paths for that directory.
For a remote TouchDrive, use the [panel host procedure](touchdrive-panel-host.md).

## Source installation

1. Install Python 3.11 or later.
2. Copy the repository to a user-owned directory.
3. Open a terminal in that directory.
4. Run `python -m backend.server --lab --visca-lab --ensure-admin`.

Use `python3` if that is your system's Python command.
The console service requires no third-party Python packages.
For desktop use, install requirements-desktop.txt and run `python camerabridge.py --tray`.

## Update and rollback

1. Select **Quit** from the tray menu, or stop the terminal service with Ctrl+C.
2. Back up the data directory and the active configuration file.
3. Extract the new release to a separate directory.
4. Start the new desktop with the previous data directory.
5. For terminal use, supply the previous `--storage` and `--config` paths.
6. Check login, camera status and stop commands.

To roll back, stop the new executable and start the previous executable with its matching data backup.
Do not run two versions against one data directory.
Do not restore or replay movement commands.

## Optional Linux user service

The supplied unit is a source-installation example.
It expects source at `~/camerabridge` and configuration at `~/.config/camerabridge/config.json`.
It does not start lab emulators.

1. Complete the foreground tests first.
2. Create the unit's configuration and data directories.
3. Copy the unit to `~/.config/systemd/user/camerabridge.service`.
4. Set its paths for your installation.
5. Run `systemctl --user daemon-reload`.
6. Run `systemctl --user start camerabridge`.
7. Check `systemctl --user status camerabridge`.

Use `journalctl --user -u camerabridge` to read its log.
Use `systemctl --user enable camerabridge` only after the tests pass.
For a package installation, replace `ExecStart` with its absolute executable path.
No Windows service or macOS launch agent is installed by this release.

## Remove the program

1. Stop CameraBridge.
2. Back up required data.
3. Remove the extracted application directory.

If you installed the Linux unit, first run `systemctl --user disable --now camerabridge`.
Then remove only its unit file and run `systemctl --user daemon-reload`.
Keep the data directory until you no longer need its records.
