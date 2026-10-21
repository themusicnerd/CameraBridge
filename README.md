# CameraBridge

CameraBridge connects native Ross DashBoard panels to one camera control service.
It includes Panasonic camera emulators and a Marshall lab model.

**Version 0.2.0rc3 is a development release. Production acceptance is incomplete.**

## Download and start

1. Open the [private release page](https://github.com/themusicnerd/CameraBridge/releases).
2. Select the package for your operating system and processor.
3. Extract the complete archive.
4. Open CameraBridge.exe on Windows, CameraBridge.app on macOS, or CameraBridge on Linux.
5. Create an administrator account in the control panel.
6. Select **Start**.
7. Select **Open setup page**.

Close the control panel to keep the service in the tray.
Right-click the tray icon and select **Quit** to stop CameraBridge.
On macOS, use the menu bar icon.
Read the [desktop procedure](docs/desktop.md) to change the port.

For a terminal service, use the applicable command.

Windows:

```powershell
.\CameraBridge-cli.exe --lab --visca-lab --ensure-admin
```

Linux or macOS:

```sh
./CameraBridge-cli --lab --visca-lab --ensure-admin
```

For terminal use, set the administrator password when the program asks for it.
Then open [CameraBridge](http://127.0.0.1:8088/) in a browser.

The packages include Python. The packages do not include Ross DashBoard.
Use the [installation procedure](docs/installation.md) for prerequisites and operating system limits.

## Open the camera panels

1. Export the panels with `CameraBridge-cli panels --output ./panels`.
2. In DashBoard, select **File > Open**.
3. Open the Panasonic or Marshall grid file in the exported directory.
4. Select **Config**.
5. Sign in with the CameraBridge account.

On Windows, use `.\CameraBridge-cli.exe` in place of `CameraBridge`.
On Linux and macOS, use `./CameraBridge-cli`.
Select **Open setup** in either panel to open its configured service address link.
Select the displayed link, or enter that address in the browser.
The browser requires a separate sign-in.

## Current scope

- The Panasonic driver implements a limited AW-HE130 command set.
- Marshall controls operate a lab model. They do not control a physical camera.
- Native camera panels have large fader handles and touch targets.
- Camera setup adds, edits, removes and numbers camera entries.
- Numbered PIVOTCam endpoints can control configured Panasonic cameras.
- Camera 1 defaults to TCP 19011. Camera 2 defaults to TCP 19012.
- Sony PXW-Z200 entries remain disabled until SDK access and integration are complete.
- Carbonite positioner and shot commands have reached the Panasonic emulator.
- An operator-triggered Custom Control recall has reached the emulator.
- Some motion packets were rejected. Continuous motion requires more tests.
- Actual switcher bus selection and positioner push/pull mapping are incomplete.
- Physical camera response and shot completion require tests.

The default lab uses local network addresses only.
The optional TouchDrive host and Carbonite relay require explicit network addresses.
See the [feature table](docs/feature-matrix.md) for the limits of each feature.

## Documentation

Start with the [documentation index](docs/index.md).
It includes installation, operation, configuration, API, security, support and developer procedures.
The [writing review](docs/ste-review.md) records the ASD-STE100 review limits.
Full ASD-STE100 compliance has not been established.

## Source installation

Python 3.11 or later is required for source use.
The console service uses the Python standard library.
The desktop interface requires PySide6 Essentials.
Install it with `python -m pip install -r requirements-desktop.txt`.
Start the desktop with `python camerabridge.py --tray`.

```sh
python -m backend.server --lab --visca-lab --ensure-admin
python -m unittest discover -v
python tools/check_docs.py
```

Read [release engineering](docs/releases.md) before you build a package.
