# CameraBridge 0.2.0rc3

This is a development prerelease.
Production and physical camera acceptance are incomplete.

## Downloads

- Windows x64: extract the ZIP archive.
- Linux x64: extract the TAR.GZ archive; GNU libc 2.35 or later is required.
- macOS Intel: select the macos-x64 archive.
- macOS Apple silicon: select the macos-arm64 archive.

Each archive includes Python and a SHA256 file is provided separately.
The packages have no publisher signature.
The macOS packages are not notarized.
Follow your organization's software approval procedure before execution.

## Changes

- Add platform packages and native package tests.
- Add a tray icon and desktop control panel.
- Add port settings, local account setup, service controls and Open setup page.
- Add camera setup with add, edit, remove and persistent camera numbers.
- Add fixed Panasonic PIVOTCam endpoints and a connection-map export.
- Set the first camera port to 19011.
- Add disabled Sony PXW-Z200 entries; Sony control is not implemented.
- Keep the service running when the control panel closes.
- Add an explicit Quit command to the tray menu.
- Add Open setup to both camera panels.
- Add the web interface to the restricted TouchDrive host.
- Retain large native fader handles and touch targets.
- Add complete procedures for the implemented release scope.
- Add a technical term list and limited documentation checks.

## Limits

Marshall hardware control, actual bus following and push/pull mapping are incomplete.
Some positioner movement packets are rejected.
The panel displays a native setup-address link.
External browser launch on the TouchDrive still requires acceptance.
Enter the displayed address in Chromium if the browser does not open.
The simulator does not establish physical shot completion or saved optical framing.
Full ASD-STE100 compliance requires the outstanding vocabulary and qualified editorial review.

Read docs/installation.md and docs/operation.md before use.
