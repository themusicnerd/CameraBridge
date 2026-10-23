# CameraBridge 0.3.0rc17

This release adds a Panasonic AK-HC1800G + AW-PH360N profile.
Connect the head through a transparent TCP/RS-422 gateway.
Set its IP address and TCP port for each camera in web setup or native DashBoard.

The profile provides pan, tilt, zoom, focus jog, iris commands, 50 shots, gain, detail, One Shot, and red tally commands.
Serial head commands report Sent because physical feedback is not available.
Autofocus mode, WB mode selection, and recall speed are not available in this profile.
Physical camera and head checks remain to be completed.

Use the current CameraBridge.grid file to add this profile in native DashBoard.
Existing HE40 settings and positioner scheduling are retained.
See [serial gateway setup](panasonic-serial.md) for the procedure.
