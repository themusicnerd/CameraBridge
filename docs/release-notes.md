# CameraBridge 0.3.0rc21

This development release adds a guided calibration workflow. Capture stationary Panasonic head and lens feedback, save a reference direction, and measure a target to estimate lens field of view at multiple zoom positions.

Save and restore camera profiles with JSON. Export lens tables for the Windows XPression adapter. Receiver addresses, ports, output switches, and camera numbers are preserved on import. Read docs/calibration.md before calibration.

The measured-target table is not a distortion solve or an Unreal Lens File. Optical center, distortion, nodal offset, focus dependence, and video timing still need image-based receiver calibration. CGI feedback does not provide frame synchronization.

Windows x64 and Linux x64 packages are included.
