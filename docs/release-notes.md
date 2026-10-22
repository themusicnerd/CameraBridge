# CameraBridge 0.3.0rc8

This development prerelease supports Windows x64 and Linux x64.
Production acceptance is incomplete.

## Changes

- Show one expandable row per camera, with a manufacturer image.
- Keep camera setup available after administrator sign-in.
- Add the Panasonic camera catalog used by the Bitfocus module.
- Add model capabilities and control limits to backend feedback.
- Add HE2 digital PTZ, iris, white balance, and shots 1 through 9.
- Prevent HE2 focus commands and unsupported model controls.
- Add the HE40 detail range and gain display scaling.
- Treat mode-restricted replies separately from transport failures.
- Confirm autofocus before accepting a rejected neutral focus command.

HE40 hardware checks confirmed zoom feedback, white-balance memory control, gain feedback, and red tally feedback.
The checks restored the starting zoom, white balance, tally state, and tally input setting.
Zoom readback differed from the requested position by one native unit.
The service reports actual feedback without inventing an exact match.

## Installation

Extract the complete platform archive.
Keep the Sony helper and its libraries with the application.
Check the supplied SHA-256 file before use.
The packages are not signed by a publisher.
See [installation](installation.md), [camera setup](camera-setup.md), and [Panasonic models](panasonic-models.md).

## Limits

A catalog entry does not mean every camera function is available.
HE40 is the only Panasonic model tested on physical hardware for this release.
Other models require hardware acceptance.
Basic CGI controls depend on the model and camera mode.
Advanced paint controls are restricted to verified command profiles.
HE2 has digital PTZ and no focus control.
HE2 absolute zoom position control is not available.
Sony PXW-Z200 remains the implemented Sony SDK profile.
FR7 and other Sony PTZ profiles are not included in this prerelease.
Marshall hardware control and actual Preset-bus following remain incomplete.
TSL 4 and TSL 5 are not supported.
Physical Carbonite tally acceptance remains required.
The documentation checks do not establish full ASD-STE100 compliance.
