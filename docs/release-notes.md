# CameraBridge 0.3.0rc20

This development release adds experimental measured FreeD output for supported Panasonic PTZ profiles. The setup page has separate Unreal and Windows XPression adapter ports. It shows measurement rate, age, and packet counts. Stale or invalid measurements stop output.

The XPression adapter uses the installed Ross Automation API. It updates an existing output scene camera and can use a measured lens field-of-view table. Read docs/camera-tracking.md before a test.

HE40 CGI feedback is slow. Output repetition does not provide frame-synchronized tracking. Lens calibration, scene alignment, and receiver testing are required.

Windows x64 and Linux x64 packages are included. This release also includes the persistent TouchDrive deployment, system statistics, and bottom bar toggle.
