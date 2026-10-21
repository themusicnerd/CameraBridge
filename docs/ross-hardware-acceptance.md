# Physical equipment acceptance

Production acceptance is incomplete.
Use isolated development equipment for these tests.
Record the model, firmware, application version and test result.

## Before a physical camera test

1. Back up the switcher configuration.
2. Record occupied device slots and input assignments.
3. Record the camera model and firmware.
4. Check the exact command specification.
5. Establish an independent camera stop method.
6. Clear the camera movement area.
7. Test the camera through its supported native controller.

The current Carbonite relay rejects physical camera targets.
Physical gateway support requires separate implementation and review.
Do not remove that guard for a test.

## Acceptance record

| Test | Required result |
|---|---|
| Manual modes and paint writes | Independent query confirms each supported value |
| Direction and inversion | Physical result agrees with the selected direction |
| Variable speed | Predictable response across the usable range |
| Simultaneous axes | Pan, tilt and zoom do not erase each other |
| Release and STOP | Camera stops within the accepted measured interval |
| Network failure | Fault indication and an independent stop method |
| Target change | Previous camera stops before a new target moves |
| Bus selection | Preset selects the intended target; Program alone does not |
| Shot recall and store | Correct shot and measured physical completion |
| Custom Controls | Recall, Recall Fast, Store and Halt act on the correct camera |
| Restart | No queued movement resumes |
| Normal switching | Camera control does not disrupt the switcher |

## Native Custom Controls

Ross documents camera events under **Devices > Camera**.
Recall Shot uses camera, channel, change type and shot number.
Store Shot uses the same selection and writes a shot.
Recall Shot Fast requests a faster recall.
Camera Halt All targets the selected camera device.

The bench verified an operator-triggered Recall Shot command to an emulator.
Recall Fast, Halt All and Custom Control Store Shot remain untested through equipment.
Menu labels must match the installed frame version.
Do not assume that a camera Custom Control can issue arbitrary HTTP commands.
