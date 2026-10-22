# Sony PXW-Z200 camera control

CameraBridge uses Sony Camera Remote SDK 2.02.00 on Windows x64 and Linux x64.
The native adapter runs in a separate process.
Camera passwords are sent through its private input pipe.
They are not command-line arguments or configuration fields.

## Set up a camera

1. Update the camera firmware as specified by Sony.
2. Enable the camera's wired LAN or wireless LAN remote function.
3. Open CameraBridge setup and sign in as an administrator.
4. Select **Add Camera**.
5. Select **Sony** under Manufacturer and **PXW-Z200** under Model.
6. Set the camera number, name, IPv4 address and Carbonite input.
7. Set the camera tally option as required.
8. Wait for **All Changes Saved**.
9. Select the camera under **Sony Camera Access**.
10. Select **Read SSH fingerprint**.
11. Verify the fingerprint through your trusted camera setup.
12. Enter the camera's remote username and password.
13. Read and acknowledge the Sony SDK terms.
14. Wait for **Camera Access Saved**.
15. Open the Sony dashboard and sign in with your CameraBridge account.
16. Confirm fresh camera feedback before control.

The SDK manages the camera connection ports.
The generic camera port field does not select a custom Sony SSH port.
SSH fingerprint changes require a new verified access record.

## Controls

The web dashboard is available at `/sony`.
The native panel is `dashboard/SW-Sony-Camera-Control.grid`.
Both interfaces provide lens jog, iris and paint controls.
The native panel uses a 1366 by 800 canvas for the TouchDrive.
It has large touch targets and the Sony identification mark.

Available controls include iris mode, focus mode, white balance mode, red gain, blue gain, gain, shutter and colour temperature.
The SDK reports each property's current value, available values and write permission.
The web interface uses these values for its controls.
Native fader requests snap to an available camera value.
Native fader limits follow the SDK's available range.
Unavailable controls remain read-only.
Camera mode can restrict a normally supported control.

Writes require a separate setting readback before confirmation.
A lens command response does not confirm physical lens movement.
The bridge has a motion watchdog and explicit stop controls.
Sony lens jog currently uses fixed direction control, rather than proportional speed.

The PXW-Z200 has no pan/tilt motors.
CameraBridge does not expose robotic head presets for this model.
Optional PIVOTCam endpoints translate supported lens and focus-mode commands.
Nonzero pan/tilt and camera preset requests are rejected.
Return the positioner to neutral when the endpoint connects.

## Tally limitation

The per-camera tally option defaults to enabled.
Sony SDK 2.02.00 does not list external tally-lamp properties for the PXW-Z200.
CameraBridge reports unsupported lamp requests for this model.
It does not use camera recording to imitate tally.
The adapter can drive red and green SDK tally properties if the connected camera exposes them as writable.
Only the PXW-Z200 connection profile is currently configured.
See [tally setup](tally.md) for routing and tests.

## Credentials and platforms

Windows protects saved camera access with Windows DPAPI for the current user.
Linux stores it in a private directory with owner-only file permissions.
Linux camera access data is not encrypted at rest.
Configuration exports and state diagnostics exclude camera access data.

Sony lists Windows 11 and Ubuntu 22.04 LTS or 24.04 LTS as tested SDK environments.
The Windows 10 development computer requires separate camera acceptance.
No physical PXW-Z200 acceptance has been completed.
SDK process fixtures test software behaviour only.

## References

- [Sony Camera Remote SDK](https://support.d-imaging.sony.co.jp/app/sdk/en/)
- [Sony SDK terms and downloads](https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement_d/en-US.html)
- [PXW-Z200 help guide](https://helpguide.sony.net/pro/z200nx800/v1/en/index.html)

The downloaded API reference contains the model capability tables.
See `function_list/device_property_list.html` and `other/compatibility.html` in that reference.
