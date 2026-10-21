# Desktop control panel

## Open CameraBridge

1. Open CameraBridge.exe on Windows, CameraBridge.app on macOS, or CameraBridge on Linux.
2. Check the data directory at the bottom of the control panel.
3. Create a local administrator account if this is the first start.
4. Select **Start**.
5. Check that the status shows the running address.
6. Select **Open setup page**.
7. Sign in to the web interface.

Passwords must be non-empty and must match the repeat field.
The application does not require a minimum password length.
Replacing an existing account requires confirmation in the control panel.
The password fields clear after the account is saved.

## Use the tray

1. Close the control panel.
2. Check that the CameraBridge icon remains in the system tray.
3. Select the icon to open the control panel again.

Windows can put the icon in its hidden-icons area.
On macOS, the icon is in the menu bar.
Linux requires a desktop that supports a system tray.
If no tray is available, closing the panel stops CameraBridge.

Right-click the icon to open the menu.
The menu contains Control panel, Open setup page, Start service, Stop service and Quit.
Stop service leaves the desktop application open.
Quit stops the owned service and exits the desktop application.
It does not stop other CameraBridge instances.

## Change the HTTP port

1. Open the control panel.
2. Set **HTTP port** to an unused port from 1024 through 65535.
3. Set **Listen address** and **Allowed client networks** if required.
4. Select **Save and restart**.
5. Check the new running address.
6. Select **Open setup page**.
7. Update the backend URL in each camera panel if the address changed.

Use 127.0.0.1 for a local service.
Simulator mode requires a loopback listen address.
For remote TouchDrive access, use the restricted panel host procedure.
Changing the HTTP port does not change a camera port, VISCA port or panel host port.

## Select camera configuration

For normal camera setup, select **Open setup page** and use **Camera setup**.
That page can add, edit, remove and number cameras without JSON editing.
Its **Save and restart** button requests a desktop service restart.
The desktop also has an **Apply saved camera setup** button.

For an external configuration file:

1. Select **Browse** beside **Camera configuration**.
2. Select a valid CameraBridge JSON file.
3. Set the simulator and VISCA options for the required test.
4. Select **Save and restart**.
5. Check the service log and camera feedback.

The desktop saves its own configuration copy in the data directory.
It applies the control panel's HTTP address, port and allowed networks to that copy.
It does not change the selected external file.
The VISCA lab and remote shot-store options require simulator mode.
Physical Marshall control is not available.

## Startup and data

Select **Start the service when CameraBridge opens** to start the service with the desktop application.
This option does not configure startup at operating system login.
Opening a second desktop with the same data directory shows the existing control panel.
Do not start a console service against the desktop's active data directory.

The data directory contains desktop-settings.json and desktop-config.json.
It also contains the service's account and camera records.
See [installation](installation.md) for the default directory on each operating system.

For source use, install requirements-desktop.txt and run `python camerabridge.py --tray`.
For a separate data directory, use `CameraBridge --tray --storage PATH`.
Use the platform's executable name and command prefix.
CameraBridge-cli runs the console service without opening a desktop window.
