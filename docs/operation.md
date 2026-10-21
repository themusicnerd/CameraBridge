# Operation

## Start and sign in

1. Start the service with the applicable [installation command](installation.md).
2. Open a native camera panel.
3. Select **Config**.
4. Set the backend URL if the service is on another host.
5. Enter the username and password.
6. Select **Sign in**.
7. Check the camera name and the SIMULATOR or HARDWARE label.

The password field clears after sign-in.
CameraBridge does not save panel login tokens to disk.
Keep passwords out of saved grid files.

## Open the web interface

1. Select **Open CameraBridge** in the panel header.
2. Sign in to the browser interface.

The button uses the backend URL on the Config page.
It first requests a DashBoard browser window.
The connected TouchDrive shows a blank browser component during the current test.
Use its displayed URL in Chromium until that platform issue is corrected.
It does not put a password or session token in the URL.
If the browser does not open, use the address in the panel status message.

## Select a camera

1. Select the camera button in the left rail.
2. Check its name and connection status.
3. Wait for confirmed feedback before an adjustment.

Camera selection stops the previous camera before the panel changes its target.
This panel selection does not change a Carbonite source or bus.

## Adjust paint or lens values

1. Select the required page.
2. Check the required manual mode.
3. Drag the fader handle, or use the large + and − buttons.
4. Check the confirmed value below the control.

For a typed value, press Enter to commit it.
Polling can replace text that you have not committed.
Use the fader or buttons for touch adjustments.
The Image page contains the second group of Marshall image controls.

## Use touch jogging

1. Select the Panasonic PTZ page.
2. Set the jog speed.
3. Select **Touch control DISABLED** to enable touch control.
4. Press a direction, zoom or focus button.
5. Release the button to stop.
6. Select **STOP** if movement continues.

The movement watchdog stops valid input after 900 milliseconds without a refresh.
This release does not send a continuous heartbeat for a held touch button.
A failed network can prevent delivery of a stop command.
Use an independent camera controller if CameraBridge cannot stop a physical camera.

## Recall or store a shot

1. Select the Panasonic Presets page.
2. Set the recall/store field to 0 for recall.
3. Select the shot button.

To store, set the field to 1 and type `OVERWRITE` before you select the shot.
Store mode clears after one selection.
Shots 1 through 20 have buttons.
The protocol and API support shots 1 through 100.
The interface does not confirm physical shot completion.

## Rename a shot

1. Set the shot number.
2. Enter the shot name.
3. Select **Save shot name**.

The service saves shot names in its data directory.

## Use administration

- **System status** shows cameras and parameter feedback.
- **Configuration** loads, imports, exports and validates configuration.
- **Paint snapshots** captures confirmed paint values.
- **Diagnostics** shows events and downloads the current state.

Only an administrator can load or save configuration, or change camera locks.
The camera setup page can request a restart from the desktop application.
For console use, restart with the saved file to apply it.
See [camera setup](camera-setup.md) for camera numbers and PIVOTCam assignments.
Snapshot recall and camera matching are not implemented.

## Stop and sign out

1. Select **STOP** for each camera that you control.
2. Check that the camera has stopped.
3. Select **Sign out**.
4. Select **Quit** from the tray menu if the service must stop.

For a terminal service, press Ctrl+C instead.
Closing the desktop control panel keeps the service running when a tray is available.
