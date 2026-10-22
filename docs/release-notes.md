# CameraBridge 0.3.0rc6

This is a development prerelease for Windows x64 and Linux x64.
Physical camera acceptance is incomplete.

## Changes

- Add one native CameraBridge panel with camera setup and manufacturer control pages.
- Add camera creation, edits, removal, Sony access, and saved-setup application in DashBoard.
- Add PIVOTCam and TSL receiver setup in DashBoard.
- Check setup revisions to prevent accidental changes from older open panels.
- Stop the previous camera before changing control pages.
- Keep the existing manufacturer panels available.

- Add a native Sony SDK 2.02.00 adapter and local camera access setup.
- Add Sony PXW-Z200 lens and paint controls with capability feedback.
- Add a Sony native DashBoard panel and a touch web dashboard.
- Add PIVOTCam lens and focus-mode translation for the Sony profile.
- Add Panasonic red tally commands and independent lamp readback.
- Add Sony SDK tally property handling with explicit unsupported-model feedback.
- Add a per-camera tally option, enabled by default.
- Add manual tally tests and a source-restricted TSL UMD 3.1 UDP receiver.
- Keep release downloads separate from Actions artifact storage.

## Installation

Extract the complete platform archive.
Keep the Sony helper and its libraries with the application.
Check the supplied SHA-256 file before use.
The packages are not signed by a publisher.
See [installation](installation.md) and [Sony setup](sony-pxw-z200.md).

## Limits

The PXW-Z200 SDK profile does not support external tally lamps or mechanical pan/tilt.
Lens jog uses fixed speed and requires physical stop acceptance.
Marshall hardware control and actual Preset-bus following remain incomplete.
TSL 4 and TSL 5 are not supported.
Physical Sony, Panasonic tally and Carbonite tally tests remain required.
The documentation checks do not establish full ASD-STE100 compliance.
