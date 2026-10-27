# Camera tracking output

CameraBridge can read the absolute head and lens encoders of supported Panasonic cameras.
It sends these values in FreeD D1 packets over UDP.
Unreal can receive these packets with Live Link FreeD.
The supplied Windows adapter can receive a second stream and control an XPression camera through its Automation API.
XPression does not receive this stream directly.

## Limits

- Use a camera on a fixed mount. Set its position and roll manually.
- This version does not measure translation, pedestal movement, or lens nodal offset.
- HE40 feedback was checked on real hardware. Other listed models need a camera test.
- Supported profiles are AW-HE40, AW-HE130, AW-HE120, AW-HE50, AW-HE60, AW-UE70, AW-HE42, and AW-UE150.
- Digital PTZ, fixed cameras, Sony handheld cameras, and the PH360 serial head do not supply a measured pose in this version.
- The default requested measurement rate is 2 Hz. Camera traffic can reduce this rate.
- Panasonic requests keep the existing 130 ms minimum interval. Control and stop requests have priority.
- The default output rate is 50 packets per second. These packets repeat the last measurement.
- Buffered interpolation can supply intermediate positions between measurements.
- Interpolation adds delay. It does not supply new measurements or frame synchronization.
- The default stale limit is 1.5 seconds. Output stops when the pan measurement exceeds this age.
- A failed or invalid head or lens query stops output until a complete valid sample is available.
- FreeD has no delivery acknowledgement. A packet count confirms transmission, not reception.

This output is experimental. Use it for static shots and slow test moves first.
Fast moves can cause a visible delay or a stepped overlay.
Do not use this CGI feedback as a substitute for a synchronized tracking system.

## Set buffered interpolation

This option is off by default. Existing camera outputs keep their previous behavior.
It applies to FreeD and the XPression adapter stream.

1. Open **Virtual Camera Tracking** in the camera row.
2. Set **Interpolation Delay (Seconds)** to 0.75 for the first test.
3. Keep the stale limit greater than the interpolation delay.
4. Enable **Buffered Interpolation Enabled**.
5. Wait for **All Changes Saved**.
6. Check for **Interpolating** in the tracking status.
7. Match the camera video delay to the rendered tracking.
8. Check the audio timing against the delayed picture.
9. Test starts, stops, reversals, tilt, and zoom before a live overlay.

The buffer uses monotonic timestamps from head and lens replies separately.
These timestamps are receipt times, not camera exposure timestamps.
The output uses linear interpolation of native encoder counts at a delayed time.
The pan angle wraps only after interpolation. Lens values are rounded to encoder counts.
No velocity prediction or extrapolation is applied.
Interpolation cannot reconstruct acceleration or a reversal between two measurements.

**Buffering** means the buffer does not yet cover the requested time for both head and lens.
No packets are sent in that state.
**Holding Latest** means the requested time is newer than the latest measurement for at least one channel.
The affected channel holds its last measured value. Increase the buffer delay if this happens repeatedly.
An output delay longer than the source interval usually provides room for interpolation.
Camera traffic and network delay can require a larger buffer.

A read error clears the buffer and stops output.
Stale feedback also clears the buffer and stops output.
Configuration changes discard the previous sample sequence.
Stopping output does not remove a graphic from the receiver. Provide an independent graphics removal control.

For an event preparation procedure, read [Unreal live logo workflow](unreal-live-logo.md).

## Set the output

1. Open the CameraBridge setup page.
2. Open the camera row.
3. Open **Virtual Camera Tracking**.
4. Set **Tracking Receiver IP** to the rendering computer address.
5. Set **Tracking Camera ID** to a unique ID at that destination.
6. Set **FreeD UDP Port** to the Unreal receiver port. The default is 40000.
7. Set **XPression Adapter UDP Port** to the adapter port. The default is 40001.
8. Set the fixed camera X, Y, and Z position in millimeters. Z is up.
9. Set the fixed roll angle in degrees.
10. Enable the required output switches.
11. Wait for **All Changes Saved**.
12. Check the measured rate, data age, and packet count below the fields.

For the current development network, the Windows receiver is `192.168.96.61`.
CameraBridge runs on TouchDrive at `192.168.96.122`.
Use different UDP ports when Unreal and the XPression adapter run on one computer.
Allow the applicable inbound UDP ports through the receiver firewall from the bridge address.
Output is off by default. Changes apply without restarting the Carbonite connection.

## Calibrate the head and lens

Use **Guided Camera and Lens Calibration** in the camera tracking foldout for stationary encoder capture and a measured-target lens table.
Read the [guided calibration procedure](calibration.md) before taking measurements.

1. Point the real camera at the reference direction for the virtual scene.
2. Read `pan` and `tilt` in `tracking_status.raw` from the diagnostic download.
3. Enter these counts in **Pan Encoder At Zero Degrees** and **Tilt Encoder At Zero Degrees**.
4. Start with **Degrees Per Encoder Count** at 0.00825. This is an approximate Panasonic value.
5. Move the camera through a measured angle.
6. Adjust the scale and inversion switches to match the virtual scene.
7. Measure lens field of view at several zoom positions.
8. Calibrate the receiver lens settings with those measurements.
9. Match the video delay and check the overlay at several pan, tilt, and zoom positions.

FreeD pan is positive clockwise from above. Tilt is positive up.
Panasonic tilt counts increase down, so **Invert Tilt** is on by default.
The packet carries native zoom and focus counts. These counts are not millimeters or focus distance.
This version does not send iris in the reserved bytes.

## Receive in Unreal

1. Enable the Live Link and Live Link FreeD plugins.
2. Restart Unreal if it requests a restart.
3. Open Live Link and add a FreeD source.
4. Set its local listen address and UDP port. Use port 40000 with the default CameraBridge setting.
5. Check that the subject camera ID agrees with CameraBridge.
6. Assign the subject to the virtual camera through a Live Link controller.
7. Set the lens encoder range to the camera range. Panasonic lens counts normally use 1365 through 4095.
8. Use a calibrated lens file for the required lens mapping and distortion correction.
9. Check axis direction, origin, image size, and video delay before an overlay test.

## Receive in XPression

The adapter requires Windows PowerShell 5.1 and an installed XPression SDK.
The commands set RemoteSigned for that process only. They do not change the computer policy.
If Windows blocks the downloaded script, check the package source, then unblock the archive in its file properties before extraction.
Its API calls were compiled against XPression Studio 11.5.1.5816.
The SDK and XPression are not included in CameraBridge packages.

1. Open XPression on the receiver computer.
2. Put the test scene on the required output framebuffer and layer.
3. Select a perspective camera in that scene. Use its rotation mode, not a look-at target.
4. Set its position, aspect, and scene units in XPression.
5. Open Windows PowerShell in `deployment/xpression` from the extracted CameraBridge package.
6. Check packets first with the following command.

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -STA -File .\Start-CameraBridgeTracking.ps1 -CheckOnly -Source 192.168.96.122 -Port 40001 -CameraId 1
```

7. Stop the packet check with Ctrl+C.
8. Start the camera adapter. Replace the scene and camera names with the names in your project.

```powershell
powershell.exe -ExecutionPolicy RemoteSigned -STA -File .\Start-CameraBridgeTracking.ps1 -Source 192.168.96.122 -Scene "Tracking Test" -Camera "Camera1" -Framebuffer 0 -Layer 0
```

9. Check pan, tilt, and roll directions with slow moves.
10. Adjust `-PanSign`, `-TiltSign`, `-RollSign`, and the three rotation offsets as required.
11. Stop the adapter. Add `-LensCsv C:\Tracking\lens.csv` after lens calibration is complete.
12. Start it again and check framing through the zoom range.

The adapter updates the named camera in the scene that is actually on the selected output layer.
It rejects a scene name mismatch. It does not load projects, put scenes on air, or select the active camera.
It preserves camera position. Set fixed position in the XPression scene.
Use the same camera orientation and scene origin for the real and virtual cameras.
The default rotation mapping is X = tilt, Y = negative pan, Z = negative roll.
Check this mapping against your scene. These defaults are not a site calibration.
The adapter accepts only the selected source IP, camera ID, valid D1 length, and valid checksum.
It discards queued older packets and stops updating when packets stop.
Use Ctrl+C to stop it. The virtual camera stays at its last position.

The lens CSV contains measured zoom counts and horizontal field of view in degrees.
Use at least two points, without a header. Lines that start with `#` are comments.
Values are interpolated between points. They are not extrapolated outside the measured range.
Without this file, the adapter leaves field of view unchanged.
It does not control focus distance or lens distortion.
This API path does not provide the synchronized camera tracking of a calibrated Lucid installation.
The live XPression scene and lens alignment still need a receiver test.

## Protocol references

- [Panasonic interface specification](https://eww.pass.panasonic.co.jp/pro-av/support/content/guide/DEF/HE50_120_IP/HDIntegratedCamera_InterfaceSpecifications-E.pdf): absolute pan/tilt and lens queries.
- [Vinten FreeD installation manual, D1 fields](https://www.manualsdir.com/manuals/641433/vinten-radamec-free-d.html?page=30): 29-byte D1 layout.
- [FreeD angle convention](https://www.manualsdir.com/manuals/641433/vinten-radamec-free-d.html?page=40) and [position units](https://www.manualsdir.com/manuals/641433/vinten-radamec-free-d.html?page=41): angles at 1/32768 degree and positions at 1/64 mm.
- [Epic Live Link FreeD guide](https://dev.epicgames.com/documentation/unreal-engine/live-link-freed?application_version=4.27): receiver and encoder setup.
- [Ross explanation of FreeD through Lucid](https://rossvideo.community/discussion/prespective-camera).
- Installed `XPressionSDK.chm`: `GetOutputFrameBuffer`, `GetSceneOnLayer`, `GetObjectByName`, `SetRotXYZ`, `FOV`, and `FOVOrientation`.
