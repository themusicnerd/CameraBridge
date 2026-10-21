# TouchDrive touch layout

Developed on Windows and visually checked in the TD1C's native DashBoard over VNC at 1920×1080. Panels retain a 1366×800 canvas to leave room for the existing tree, menu and tab bar. No display resolution, DashBoard theme or switcher configuration was changed for this update.

- Native vertical fader widget 26 replaces small dot sliders. Handles render approximately 120×40 screen pixels on this TD setup.
- Navigation targets are 104×56. Command buttons, numeric fields and login fields are at least 48 pixels high. Fixed rail STOP is 124×64; the PTZ pad has a second large STOP.
- Marshall Paint contains red gain, blue gain, black level and gamma. Image contains colour, sharpness, brightness and gain. Exposure uses large value fields and bounded +/− buttons.
- Panasonic retains PTZ, Presets (20 shots), Paint, TD1C and Config. Manufacturer logos remain in the header.
- Fine +/− adjustment uses native parameter bindings and the existing authenticated write path. Slider range limits, access and backend mode checks remain in effect.

Both panels opened natively and authenticated on the TD. Panasonic iris fader drag reached 2834 with confirmed CGI emulator readback, then the value field restored 1365 with confirmed readback. Marshall black level +/− changed 0 → 1 → 0 with confirmed lab model feedback. Touch jogging was left disabled. No physical camera was used for these interface checks.

Seven panel/host tests pass, including geometry bounds, minimum touch target sizes, fader presence, event bindings and host access restrictions. The Node smoke test parses 104 Panasonic and 71 Marshall handlers and exercises live feedback. Screenshots below are actual TD VNC captures, not mockups.

![Panasonic paint](images/touch-panasonic-paint.png)

![Marshall paint](images/touch-marshall-paint.png)

Current deployed files are `/home/touchdrive/Downloads/CameraBridge-Panasonic (1).grid` and `/home/touchdrive/Downloads/CameraBridge-Marshall (1).grid`. Older panels remain available as a rollback. The panel host serves the regenerated sources at `/Panasonic.grid` and `/Marshall.grid` on the explicitly configured LAN development host.

Movement packet rejection, push/pull mapping, actual Preset-bus following and physical shot completion are separate outstanding control work. This layout update does not claim to resolve them. Numeric text fields commit on Enter; ongoing polling can still interrupt uncommitted text, so the larger faders and +/− buttons are the preferred touch adjustments.
