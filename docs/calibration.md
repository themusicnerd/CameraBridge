# Guided camera and lens calibration

This procedure saves a camera reference direction and a measured-target lens table.
The table estimates horizontal field of view at a fixed focus setting.
It is not an image-based distortion solve.

For image-based calibration, use the [video workstation](video-calibration.md).
It accepts NDI, RTSP, and Magewell USB capture, then solves checkerboard images with OpenCV.
It can save optical results to the camera profile without changing the head or receiver settings.

## Prepare the camera

1. Attach the camera to its fixed mount.
2. Set the video format, resolution, and image crop that you will use.
3. Disable digital zoom and image stabilization for the calibration test.
4. Set focus to manual. Keep the same focus setting for the lens table.
5. Open the camera row in CameraBridge Setup.
6. Open **Virtual Camera Tracking**.
7. Open **Guided Camera and Lens Calibration**.

Changes to crop, digital zoom, focus, or stabilization can change image geometry.
Use a new profile when the image geometry changes.

## Set the reference direction

1. Point the real camera at the zero direction of the virtual scene.
2. Stop pan, tilt, zoom, and focus.
3. Select **Read Stationary Encoders** to check the feedback.
4. Select **Use Current Direction As Zero**.
5. Wait for **All Changes Saved**.
6. Open **Head and Fixed Mount Calibration**.
7. Set the measured mount position and roll.
8. Check the pan and tilt direction with slow moves.
9. Check the encoder scale through a measured angle.

Each capture reads the head and lens twice.
It rejects changed encoder values or a queued control command.
It does not move the camera or store a camera preset.
The software cannot select a physical scene reference for you.

The fixed position is included in FreeD.
The XPression adapter preserves scene position. Set its position in the XPression scene.

## Measure the lens

1. Use a flat target of known width.
2. Keep the target centered and perpendicular to the camera view.
3. Measure the distance from the lens entrance pupil to the target plane.
4. Enter **Profile Name**, **Video Width**, and **Video Height**.
5. Enter **Target Width** and **Lens to Target Distance** in millimeters.
6. Measure the target width in pixels in the full-resolution camera image.
7. Enter **Target Width in Image**.
8. Stop the camera and lens.
9. Select **Capture and Add Lens Point**.
10. Wait for **All Changes Saved**.
11. Repeat at wide, middle, and tele zoom positions.
12. Add more points where the field of view changes rapidly.

Use the uncropped image at the selected video resolution.
Do not measure a scaled preview unless you convert its pixel width to the full image width.
Use the optical entrance pupil as the distance reference, not the camera base.
An incorrect distance gives an incorrect field of view, especially at short distances.
If you cannot locate that reference accurately, use image-based calibration in the renderer.

The calculation uses the perspective projection equation:

```text
fx_pixels = distance_mm * target_pixels / target_width_mm
horizontal_fov_degrees = 2 * atan(video_width / (2 * fx_pixels)) * 180 / pi
```

This estimate assumes a flat target normal to the optical axis.
Distortion can affect the pixel measurement.
It does not calculate distortion, principal point, lens breathing, or nodal offset.
The saved focus encoder helps you check that focus stayed fixed.
The interface reports a focus change greater than 20 encoder counts.
This threshold is a capture warning, not a measured lens tolerance.

Use one point per zoom encoder in a profile.
Remove an old point before you capture a replacement at that zoom.
Remove saved lens points before changing video dimensions.

## Save and use a profile

1. Select **Export Calibration Profile** to save the head settings and lens measurements as JSON.
2. Select **Import Calibration Profile** to restore a profile for the same camera model.
3. Check the mount position and reference direction after import.
4. Select **Export XPression Lens CSV** after at least two lens points are saved.
5. Start the Windows adapter with `-LensCsv` and the exported CSV path.

Import does not change receiver IP, UDP ports, output switches, or camera number.
It checks the profile structure, value ranges, target calculation, and camera model before applying data.
It does not establish that two physical cameras of the same model have the same calibration.
Use the profile from the actual camera and lens that you will operate.

For Unreal, use the measurements as reference while you calibrate a Lens File.
The JSON export is not an Unreal Lens File asset.
FreeD continues to transmit the native zoom and focus encoders.
The calibration table does not change those wire values.

## Complete optical and timing calibration

Use the video workstation to estimate image distortion and optical center from camera images.
Use those results with the correct lens model in your renderer.
Nodal offset and video timing still need separate calibration.

1. Supply camera images to the rendering computer.
2. Use a measured checkerboard or another supported calibration target.
3. Calibrate image distortion, optical center, and lens nodal offset in the renderer.
4. Repeat the optical calibration at the required zoom and focus settings.
5. Check a virtual reference at the center and edges of the image.
6. Check alignment at several head angles and zoom positions.
7. Match video and tracking delay with slow moves.

CameraBridge does not mark these steps complete after target measurements.
Its CGI tracking rate remains limited by camera feedback.
Calibration does not increase that rate or synchronize it to video frames.

## References

- [Epic lens calibration overview](https://dev.epicgames.com/documentation/unreal-engine/camera-lens-calibration-overview): lens information, distortion, image center, and nodal offset.
- [Epic camera calibration quick start](https://dev.epicgames.com/documentation/unreal-engine/camera-lens-calibration-quick-start-for-unreal-engine): Lens File and checkerboard procedure.
- [OpenCV calibration documentation](https://docs.opencv.org/5.0/main_modules/calib.html): camera intrinsics and perspective projection.
