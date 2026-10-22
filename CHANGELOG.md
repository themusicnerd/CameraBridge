# Change record

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
