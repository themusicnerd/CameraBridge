# Change record

## 0.3.0rc24

- Add optional buffered interpolation to FreeD and XPression tracking output.
- Timestamp head and lens replies separately. Do not extrapolate movement.
- Show buffering, interpolating, and holding states in camera setup.
- Document the HE130 to Unreal live logo workflow and its remaining venue checks.

## 0.3.0rc23

- Correct the workstation logo asset path in native packages.
- Restore source type, board settings, camera link, and lens tags when the workstation page reloads.
- Verify the packaged workstation page, logo, and authenticated state during release checks.

## 0.3.0rc22

- Add a local video calibration workstation to the tray and console.
- Receive NDI through the installed runtime.
- Receive RTSP and Magewell USB capture through an external FFmpeg executable.
- Show source selection, requested USB capture dimensions, and live preview.
- Capture checkerboard views at native resolution and solve pinhole lens intrinsics and distortion.
- Reject stale frames, repeated views, and unconstrained flat-view batches.
- Export optical profiles and save linked camera results to CameraBridge.
- Preserve head, receiver, and camera-number settings when importing optical-only results.
- Prefer solved field of view in exported XPression lens tables.

## 0.3.0rc21

- Add stationary encoder capture and reference-direction capture.
- Add a guided measured-target lens calibration table per camera.
- Save profile names, video dimensions, target measurements, and focus encoder values.
- Export and import camera calibration profiles without changing receiver settings.
- Export lens tables for the Windows XPression adapter.
- Explain the remaining image distortion, nodal offset, and timing calibration steps.

## 0.3.0rc20

- Add measured Panasonic head and lens feedback for experimental FreeD output.
- Set receiver ports, camera ID, fixed mount position, and encoder calibration per camera.
- Show measured rate and data age separately from output packet counts.
- Stop output after invalid or stale camera feedback.
- Add a Windows FreeD-to-XPression Automation API adapter and a calibration guide.
- Include the persistent TouchDrive deployment, system monitor, and bottom bar toggle.

## 0.3.0rc18

- Remove the obsolete TouchDrive page from Panasonic control panels.
- Register direction-pad press, release, and exit events against explicit control IDs.
- Center number fields and show their current model ranges.
- Add a touch numeric popup with staged input, Enter, Cancel, and range checks.
- Record completed dashboard movement requests for control verification.
- Clarify the limited AK-HC1800G paint coverage.

## 0.3.0rc17

- Add AK-HC1800G on AW-PH360N through a transparent TCP/RS-422 gateway.
- Set a separate gateway IP and TCP port for each camera.
- Add the combined profile to web setup and native DashBoard.
- Report serial head commands as sent without invented feedback.
- Preserve the PH360 lens extender by keeping autofocus mode unavailable.

## 0.3.0rc16

- Reject movement queued before a stop, without requiring a new neutral sequence.

- Accept positioner movement immediately on a fixed camera port.
- Give motion and stop requests priority over camera polling.
- Keep camera access free while the polling worker waits during movement.
- Deliver neutral stop packets even when they exceed the movement expiry limit.
- Skip repeated confirmed speed commands while renewing the movement watchdog.
- Add optional local timing capture for PIVOTCam input and camera HTTP output.

## 0.3.0rc14

- Prevent neutral Carbonite keepalives from taking dashboard ownership.
- Release idle ownership after a confirmed paint write.

## 0.3.0rc13

- Use the native global range-constraint API supported by TouchDrive DashBoard.
- Keep all feedback fields updating and handle empty replies.

## 0.3.0rc12

- Parse HE40 OGR and OGB gain query replies, as confirmed on the camera.

## 0.3.0rc11

- Align fader endpoint labels and buttons with high-up slider values.
- Serialize jog and release requests; coalesce direction changes and renew held controls.
- Stop unknown axes after ambiguous motion failures.
- Save a recall speed per shot and accept a speed override on recall.
- Apply saved speeds to Carbonite and custom-control recalls.
- Add ATW, Manual A, Manual B, and One Shot controls with mode and gain feedback.
- Use the HE40-family red and blue gain commands.

## 0.3.0rc10

- Wait for confirmed camera mode before the packaged iris test.
- Clarify downloaded panel names in TouchDrive installation Help.

## 0.3.0rc9

- Add inline camera setup, automatic save and application, switches, and separate manufacturer/model lists.
- Add persistent device sign-in and an authentication option.
- Add TSL packet status, tally colours, and separate lamp readback.
- Restore the tray control panel reliably after a hidden launch.
- Remove simulator startup from new installations and simplify setup.
- Add IP links, identification artwork, and setup Help.


## 0.3.0rc8

- Add expandable camera rows and manufacturer identification images.
- Add the Panasonic model catalog from the Bitfocus module.
- Add HE2 digital PTZ, iris, white balance, and its nine-shot limit.
- Disable controls that are unavailable in a model profile.
- Add HE40 detail range and gain display scaling.
- Handle mode-restricted feedback and autofocus neutral commands.
- Verify HE40 zoom, white balance, gain feedback, and red tally on real hardware.
- Preserve the observed camera settings after hardware checks.

## 0.3.0rc7

- Load camera setup automatically after administrator sign-in.
- Fix Add camera when setup was opened before sign-in.
- Show account access, setup loading, load errors, and retry controls.
- Clear camera drafts and access fields on sign-out or session expiry.
- Place the camera form before the roster and group network settings in a separate section.
- Show unsaved changes and the camera's PIVOTCam port.
- Test the browser sign-in, setup failure, retry, and session-expiry paths.

## 0.3.0rc6

- Add a unified native DashBoard panel for camera setup and camera control.
- Add camera type, address, camera number, Carbonite input, and tally options in that panel.
- Add Sony access setup without storing passwords in the grid file.
- Add PIVOTCam and TSL receiver settings in DashBoard.
- Check configuration revisions before saving camera setup.
- Stop the previous camera before changing control pages.
- Preserve the separate manufacturer panels.

## 0.2.0rc3

- Add native release packages for Windows, Linux and both macOS processor types.
- Add a separate build and package test for each platform.
- Add a desktop control panel and tray menu.
- Keep the service running when the control panel closes.
- Add saved port settings, service controls and local account setup.
- Add a camera editor with persistent camera numbers and a PIVOTCam map export.
- Add fixed Panasonic PIVOTCam endpoints restricted to one controller address.
- Set the default first camera port to 19011.
- Add disabled Sony PXW-Z200 entries and record the SDK access requirement.
- Store packaged application data outside the application directory.
- Add a panel export command with local manufacturer images.
- Add **Open setup** to both native panels.
- Serve the CameraBridge web interface through the restricted TouchDrive host.
- Add installation, operation, API, configuration and release procedures.
- Correct obsolete test and platform statements.
- Add a technical term list and limited documentation checks.
- Record the remaining ASD-STE100 review requirements.

## Earlier development work

- Add separate Panasonic and Marshall native panels.
- Add large fader handles and touch controls.
- Test the TouchDrive layout at 1920 × 1080.
- Observe Carbonite positioner, shot store and shot recall commands.
- Observe a Custom Control recall at the Panasonic emulator.

The release does not add physical camera acceptance or actual switcher bus feedback.
