# Desktop control panel

## Open CameraBridge

1. Open CameraBridge.exe on Windows, CameraBridge.app on macOS, or CameraBridge on Linux.
2. Check the data directory at the bottom of the control panel.
3. Create a local administrator account if this is the first start.
4. Select **Start**.
5. Check that the status shows the running address.
6. Select **Open Setup Page**.
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
The menu contains Control Panel, Open Setup Page, Start Service, Stop Service and Quit.
Stop Service leaves the desktop application open.
Quit stops the owned service and exits the desktop application.
It does not stop other CameraBridge instances.

## Change the HTTP Port

1. Open the control panel.
2. Set **HTTP Port** to an unused port from 1024 through 65535.
3. Set **Listen Address** and **Allowed Client Networks** if required.
4. Select **Save and Restart**.
5. Check the new running address.
6. Select **Open Setup Page**.
7. Update the backend URL in each camera panel if the address changed.

Use 127.0.0.1 for a local service.
For remote TouchDrive access, use the restricted panel host procedure.
Changing the HTTP Port does not change a camera port, VISCA port or panel host port.

## Select camera configuration

For normal camera setup, select **Open Setup Page** and use **Cameras**.
That page can add, edit, remove and number cameras without JSON editing.
Camera row changes save and apply automatically without ending browser sign-in.
The desktop also has an **Apply Saved Camera Setup** button.

For an external configuration file:

1. Select **Browse** beside **Camera Configuration**.
2. Select a valid CameraBridge JSON file.
3. Check the selected configuration path.
4. Select **Save and Restart**.
5. Check the service log and camera feedback.

The desktop saves its own configuration copy in the data directory.
It applies the control panel's HTTP address, port and allowed networks to that copy.
It does not change the selected external file.
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
