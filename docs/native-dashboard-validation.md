# Native application tests

The development host uses Ross DashBoard 9.15.2 on Windows x64.
The connected TouchDrive also runs native DashBoard panels.
Windows screen capture failed during early tests.
Later TouchDrive VNC captures provided actual native layout evidence.
The earlier screen-capture failure is not a current layout test blocker.

## Passed checks

- Both grid files loaded as native panels.
- Native timers and HTTP requests ran repeatedly.
- The normal feedback path updated parameter values and labels.
- Both panels accepted the existing CameraBridge login.
- Native simulator writes produced independent confirmed feedback.
- The large fader layout fit the TouchDrive screen.
- Panasonic shot recall reached the backend.

Instrumented early panels sent feedback-success requests after the normal callback completed.
These temporary files are not release dependencies.
The JavaScript smoke test provides additional script checks outside the native runtime.
It does not replace native tests.

See [touch layout tests](touch-layout-validation.md) for screen captures and reversible value changes.
See [lab protocol tests](ross-lab-protocol.md) for Carbonite traffic.
Physical camera response, every touch gesture and platform-specific browser launch still require acceptance checks.

## Unified panel acceptance

The unified panel was checked on the TD1C through its 1920 × 1080 VNC desktop.
The test used a separate source backend and the existing loopback Panasonic simulators.
The main Windows tray service stayed unchanged during these checks.

- The 1366 × 872 panel loaded in native DashBoard.
- The setup page fit the screen with the navigation views open.
- Manufacturer and ON/OFF choices displayed as dropdown lists.
- Number fields displayed as entry controls with increment buttons.
- Native administrator sign-in loaded all three simulator camera entries.
- A native camera-name edit reached the pending configuration file.
- The saved test edit was removed after verification.
- Camera selection opened the Panasonic PTZ page with authenticated feedback.
- Iris readback showed a confirmed simulator value.

These checks do not establish physical camera operation or native operation on another operating system.
Automated checks cover camera setup authorization, revisions, credentials, and packaged API operation.
