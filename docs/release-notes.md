# CameraBridge 0.3.0rc13

Windows x64 and Linux x64 packages include these control updates.

- Put Open and Tele at the high end of the native faders.
- Put Close and Wide at the low end.
- Serialize quick direction changes and button releases.
- Send changed movement axes and stop all axes with unknown state.
- Save a speed from 1 to 30 for each shot.
- Apply saved speeds to panel, Carbonite, and custom-control recalls.
- Set an override speed for one recall without changing the saved speed.
- Add ATW, Manual A, Manual B, and One Shot controls.
- Show mode and gain feedback with camera readback.
- Correct HE40-family gain query and control commands.

One Shot command delivery is reported separately from completion.
Camera completion notifications are not received in this release.
Preset motion completion is also not confirmed.

See [Help](quick-start.md) for control procedures.
