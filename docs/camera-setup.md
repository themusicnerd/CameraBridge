# Camera setup and PIVOTCam assignments

## Add a real camera

1. Open the setup page from the desktop control panel.
2. Sign in as an administrator.
3. Select **Camera setup**.
4. Select **Add camera**.
5. Set a unique camera number and name.
6. Select the camera profile.
7. Set the camera address and connection port.
8. Set the Carbonite video input.
9. Enable the camera if its driver is available.
10. Select **Save camera to setup**.
11. Select **Save and restart**.
12. Check the running camera identity and confirmed feedback.

Administrator sign-in opens camera setup and loads the camera list automatically.
Wait for the setup-ready message before selecting **Add camera**.
The camera form appears before the camera rows.
Saving a camera to the draft does not connect it immediately.
Select **Save and restart** to apply the draft.
Sign in again after the service restarts.

If loading fails, select **Reload setup** to try again.
Operator accounts cannot change camera setup.
Sign-out clears the local draft and hides its editor.
Open **Switcher and tally network settings** to change the receiver settings.

The Panasonic catalog includes AW-HE2 and the models listed by the Bitfocus module.
See the [model and control limits](panasonic-models.md).
Select the row arrow to show the camera assignments and Edit and Remove buttons.
The camera port is normally 80 for that profile.
The camera connection port is separate from the PIVOTCam listening port.
Sony setup uses the SDK adapter and a separate local camera access form.
Physical Marshall entries must remain disabled.

The desktop stops its old service before starting the saved setup.
When a physical camera is enabled, the desktop disables simulator startup and the legacy VISCA lab.
A console service saves config.pending.json and requires an explicit restart with that file.

## Edit or remove a camera

1. Select **Camera setup**.
2. Select **Edit** or **Remove** on the required camera card.
3. Complete the edit or confirm removal.
4. Select **Save and restart**.
5. Check the resulting camera list.

The internal camera ID remains stable during edits.
Changing a camera number changes its PIVOTCam port after restart.
Removing a camera does not renumber the remaining cameras.
Removal stops the previous service before the new camera list starts.

## Assign PIVOTCam

1. Enable **PIVOTCam control** on each required Panasonic camera entry.
2. Enable **numbered PIVOTCam endpoints** in the network section.
3. Set the CameraBridge listen IP to its address on the control network.
4. Set the Carbonite controller IP.
5. Keep the base port at 19010 unless a different range is required.
6. Select **Save and restart**.
7. Select **Export PIVOTCam map**.
8. Set each Carbonite PIVOTCam device to its exported CameraBridge address and port.
9. Use VISCA address 1 on each connection.
10. Assign each device to its required Carbonite video input.
11. Test neutral, movement, stop and recall before use.

| Camera number | Default TCP port |
|---|---|
| 1 | 19011 |
| 2 | 19012 |
| 3 | 19013 |

The port is the base port plus the camera number.
Each endpoint controls one fixed camera.
The endpoint accepts only the configured controller IP.
Permit the required TCP ports in the host firewall for that controller.
The camera number, Carbonite video input and VISCA address have different functions.
This service does not infer or follow the actual switcher Preset bus.

Return pan/tilt and zoom to neutral after a stop or connection change.
The 900 millisecond watchdog remains active.
Remote shot storage is disabled unless the camera entry explicitly permits it.
The software does not confirm physical shot completion.
