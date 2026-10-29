# CameraBridge 0.3.0rc26

This development release adds Panasonic VAR white balance and Kelvin entry.
Use Paint in CameraBridge.grid, or expand the camera row in the web setup page.
Select VAR / Kelvin, wait for confirmed feedback, then enter the colour temperature.

HE130 supports 2000 through 15000 K through a camera-specific lookup table.
HE40 supports 2400 through 9900 K in steps of 100 K.
The bridge uses the nearest supported value and checks the camera readback.
HE2 retains its documented white-balance modes and does not offer VAR Kelvin entry.

PIVOTCam feedback now reports the connection, frame count, and last camera control result.
Duplicate active Panasonic camera endpoints are rejected during setup.
Background polling and tracking release camera access during pacing waits.
Their queue positions are retained so feedback cannot be starved by tracking queries.
Fresh focus feedback answers Carbonite inquiries without an extra camera request.

Read the [Panasonic guide](panasonic-aw-he130.md) for commands and operating limits.

Windows x64 and Linux x64 packages are included.
