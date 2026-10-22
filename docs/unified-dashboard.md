# CameraBridge native panel

Open `CameraBridge.grid` in Ross DashBoard.
The panel uses a 1366 × 872 canvas.
It contains camera setup and the Panasonic, Sony, and Marshall control pages.
It does not embed a browser.

## Connect to CameraBridge

1. Select **Cameras / setup**.
2. Enter the bridge URL.
3. Enter your CameraBridge username and password.
4. Select **Sign in**.

Use the panel-host URL on a TouchDrive.
The development host uses `http://192.168.96.61:8089`.
Do not use the TouchDrive loopback address for a backend on Windows.
Use an administrator account to change setup.
An operator can load the running camera list and use camera controls.

The sign-in password field clears before the request.
The session token stays in memory.
The panel does not contain a stored account password.
Do not save an edited grid while a password field contains text.
The development panel host uses plain HTTP on the isolated bench network.
See [security](security.md) before use on another network.

## Add a camera

1. Select **New** on **Camera settings**.
2. Enter the camera name.
3. Select its manufacturer and model.
4. Enter its IP address and port.
5. Set a unique camera number.
6. Set the Carbonite input number.
7. Set the camera, PIVOTCam, preset-store, and tally options.
8. Set the TSL tally address.
9. Select **Save**.
10. Select **Apply saved setup**.

The desktop service applies the saved configuration through its existing restart procedure.
Wait for the restart. The open panel keeps its session token.
A console service cannot restart itself through this panel.
Restart that service with `config.pending.json` to apply its saved setup.
Saving alone does not change the running cameras.

Select a camera in the list to edit it.
The list has eight cameras per page.
Use **Previous** or **Next** to change pages.
For removal, select the camera and enter `REMOVE` in the confirmation field.
Select **Remove**, then apply the saved setup.

Reload the list if another panel changes setup.
The backend rejects a save from an older setup revision.
Existing camera IDs stay unchanged when their camera numbers change.

## Set Sony access

1. Save a Sony PXW-Z200 camera.
2. Select that camera in the list.
3. Select **Camera access**.
4. Enter the camera username and password.
5. Select **Read fingerprint**.
6. Compare the fingerprint with the camera identity.
7. Read the Sony SDK terms at the address shown on the panel.
8. Set the terms acknowledgement to **YES** if you accept them.
9. Select **Save camera access**.

The camera password field clears before the request.
The bridge stores access separately from its configuration.
Windows uses account-bound credential protection.
Linux uses owner-only access files.
Passwords are not read back to the panel.
See [Sony setup](sony-pxw-z200.md) for camera requirements and control limits.

The Panasonic driver does not implement HTTP authentication.
Marshall hardware profiles remain disabled until their driver is available.
The Marshall simulator transmits no serial packets.

## Set PIVOTCam and tally receivers

1. Select **Bridge / interop**.
2. Set the PIVOTCam listen IP to an address on the bridge host.
3. Enter the allowed Carbonite source IP.
4. Set the first camera TCP port.
5. Enable the PIVOTCam receiver if required.
6. Set the TSL 3.1 receiver IP, source IP, and UDP port.
7. Enable the tally receiver if required.
8. Select **Save bridge settings**.
9. Select **Apply saved setup**.

Camera number 1 uses TCP port 19011 by default.
Camera number 2 uses port 19012.
Each camera must also have its PIVOTCam option enabled.
Allow the selected ports through the bridge host firewall.
The panel does not change firewall rules or configure the switcher.

Carbonite defaults to tally 2 for Program and tally 1 for Preview.
The default input-to-TSL address offset is zero.
An explicit per-camera tally address overrides that offset.
Each new camera has tally enabled by default.
The global tally receiver stays off until configured.
See [tally](tally.md) for protocol and camera limitations.

## Control a camera

1. Select a running camera in the list.
2. Select **Control selected camera**.
3. Enable touch control before a lens or PTZ jog.

The panel shows the selected manufacturer and its control pages.
Changing cameras sends a stop to the previous camera.
A failed stop prevents the change.
Hidden manufacturer pages cannot send control commands.
The Panasonic pages retain preset and TouchDrive integration controls.
The Sony Z200 has no pan/tilt motors.
Its external tally lamp remains unsupported where the SDK exposes no writable lamp property.

## Export or host the panel

Run `CameraBridge-cli panels --output PATH` to export the panel and logo files.
Keep the `assets` directory with the exported files.
For a TouchDrive, download `/CameraBridge.grid` from the panel host.
That download contains HTTP image paths and the panel-host bridge URL.
The backend and panel host must both include the unified setup API.
An older running application cannot provide these setup functions.

See [native validation](native-dashboard-validation.md) for test scope.
