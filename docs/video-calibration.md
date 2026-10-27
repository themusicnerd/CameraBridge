# Video calibration workstation

Run this tool on the computer that receives camera video.
Camera control can stay on the TouchDrive.
The workstation supports these inputs:

| Input | Connection | Required runtime |
|---|---|---|
| NDI | Select a discovered NDI source | Installed NDI runtime |
| RTSP | Enter the camera stream URL | FFmpeg with RTSP input |
| USB Capture (Magewell) | Connect SDI or HDMI to the Magewell, then USB to the computer | FFmpeg and a system video-capture device |

Windows uses DirectShow for USB video.
Linux uses Video4Linux2.
Magewell USB Capture devices appear as video-capture devices.
This tool does not need the Magewell proprietary capture SDK.
Use the software and firmware required by your actual device model.

## Open the tool

1. Start CameraBridge on the video computer.
2. Right-click its tray icon.
3. Select **Open Video Calibration**.

You can also select that button in the control panel.
The camera-control service does not have to run on this computer.
The workstation listens only on the local loopback address.
It does not expose a second camera-control service to the network.
Closing the browser keeps the tool in the CameraBridge tray.
Select **Stop Preview** to release the video source.
Select **Quit** in the tray to stop the application and video tool.

For console use:

```powershell
.\CameraBridge-cli.exe calibration
```

On Linux:

```sh
./CameraBridge-cli calibration
```

The console command uses local port 8090 by default.
Use `--port` to change it.
Use `--no-browser` to start without opening a browser.
Use `calibration --check-dependencies` to check the installed video runtimes.

## Install video runtimes

Native packages include NumPy and OpenCV.
They do not include the NDI runtime or an FFmpeg executable.

For NDI, install the official NDI runtime for the workstation operating system.
The tool checks the standard runtime locations and the NDI runtime environment variables.
Linux can also load `libndi.so.6` or a runtime library in the system library search path.

For RTSP or USB, install FFmpeg and put its executable on PATH.
You can instead set `CAMERABRIDGE_FFMPEG` to its full executable path before starting CameraBridge.
Use a build with DirectShow input on Windows or Video4Linux2 input on Linux.
FFmpeg remains an external program with its own license and installation.

For source development, install the video dependencies:

```sh
python -m pip install -r requirements-video.txt
```

## Select video

### NDI

1. Select **NDI**.
2. Select **Discover Sources**.
3. Select the camera source by name.
4. Select **Start Preview**.
5. Check the source image and actual video dimensions.

Discovery does not open a source preview.
Only **Start Preview** starts receiving the selected source.
If a new source is missing, let its sender start, then discover again.
Check NDI discovery and network access with the sender software if needed.

### RTSP

1. Select **RTSP**.
2. Enter the full camera stream URL.
3. Enter a username and password if the camera requires them.
4. Select **Start Preview**.
5. Wait for the stream decoder to receive a keyframe.
6. Check that the selected stream uses the required resolution and crop.

Use the stream address from the camera documentation.
Do not assume that different camera models use the same path.
RTSP uses TCP transport for this workflow.
Credentials are not saved in a calibration profile.
The password field clears after the start request.

### USB Capture (Magewell)

1. Connect the camera SDI or HDMI output to the Magewell.
2. Connect the Magewell USB output to this computer.
3. Select **USB Capture (Magewell)**.
4. Select **Discover Sources**.
5. Select the Magewell video device.
6. Enter the required capture width and height.
7. Select **Start Preview**.
8. Check the actual video dimensions shown above the image.

Leave both capture dimensions blank to use the device default.
The default can differ from the camera video format.
Use the full image format required for the overlay.
If the device is busy, release it in the other capture application first.
Audio is not used for calibration.

## Link encoders

1. Enter the CameraBridge address in section 2.
2. Enter a CameraBridge administrator account.
3. Select **Connect to CameraBridge**.
4. Select the camera that supplies this video.
5. Select **Read Camera Encoders** while the camera and lens are stationary.

For the current development network, the bridge address is `http://192.168.96.122:8088`.
The password is used for sign-in and then discarded.
The session token stays in workstation memory until the tool closes.
The tool sends no movement or preset commands.
When linked, every accepted board capture checks the camera lens encoders.
It rejects a changed camera or lens setting within one batch.
Current automatic encoder capture uses the supported mechanical Panasonic profiles.

For another camera, enter manual model, zoom, and focus tags.
Leave both encoder fields blank to make an untagged optical solve.
An untagged solve cannot be assigned automatically to a CameraBridge camera.
Match the physical video source to the selected camera yourself.

## Capture a checkerboard batch

1. Select the inner corner columns and rows.
2. Select **Download Checkerboard SVG** if you need a pattern.
3. Print the pattern at 100% size with a white outer border.
4. Measure a printed square and enter its actual size in millimeters.
5. Attach the pattern to a flat, rigid surface.
6. Lock camera zoom and focus at the lens setting to be calibrated.
7. Keep image crop, stabilization, and video dimensions fixed.
8. Wait for the lens and video to settle.
9. Show the complete board in the preview.
10. Select **Capture Board Image**.
11. Move and tilt the board before the next capture.
12. Capture at least 12 different views.

Cover the image center and edges.
Include board tilts in both directions and different distances.
Do not use only flat translations of the board.
The tool rejects repeated views, very small boards, stale video, and unconstrained flat-view batches.
It permits up to 30 views in one batch.
The solve uses full-resolution frames. The displayed preview can be smaller.
Video input is limited to 4096 by 2160 pixels.
Saved samples contain detected corner coordinates in memory, not a persistent video recording.

## Solve and inspect

1. Select **Solve Lens Calibration**.
2. Check the RMS reprojection error and the error for each view.
3. Check focal lengths and optical center against the actual image.
4. Check the result against independent images that were not used in the solve.
5. Repeat with better board coverage if the result is unstable.

The model is the OpenCV pinhole model with five distortion coefficients.
Their order is `k1, k2, p1, p2, k3`.
Focal lengths and optical center are stored in pixels and normalized image coordinates.
The solver reports a warning above 1 pixel RMS.
That threshold is a diagnostic hint, not a production acceptance test.
A low fitting error does not prove that an overlay will align.

The tool does not solve lens nodal offset or video timing.
Those fields remain explicitly uncalibrated in the result.
It does not increase the camera tracking rate or provide frame synchronization.

## Save and repeat

1. Select **Export Optical Calibration JSON** to save the result.
2. If linked to a camera, select **Save to CameraBridge**.
3. Check the saved optical result in the camera tracking calibration foldout.
4. Select **New Lens-Setting Batch** before changing zoom or focus.
5. Capture and solve the next lens setting.

Direct save preserves camera number, receiver addresses, ports, output switches, and head calibration.
It replaces an optical solve at the same zoom encoder.
A profile permits up to 16 optical zoom settings.
Use a separate exported profile when you need another focus table or video format.
The tool refuses to apply an unrelated pending camera setup.

You can import a tagged optical JSON file with **Import Calibration Profile** in CameraBridge Setup.
Optical-only import preserves the existing head calibration and measured-target points.
For XPression, the lens CSV uses solved field of view in preference to a target estimate at the same zoom.
It does not convert OpenCV distortion coefficients to XPression lens-correction parameters.
For Unreal, transfer the result using the correct lens model and Lens File workflow.
The JSON file is not an Unreal Lens File asset.

## References

- [Magewell USB Capture HDMI Gen 2 specifications](https://www.magewell.com/tech-specs/usb-capture-hdmi-gen-2): supported capture interfaces.
- [FFmpeg capture-device documentation](https://ffmpeg.org/ffmpeg-devices.html): DirectShow and Video4Linux2 inputs.
- [NDI receive documentation](https://docs.ndi.video/all/developing-with-ndi/sdk/ndi-recv): video receive API.
- [NDI runtime distribution](https://docs.ndi.video/all/developing-with-ndi/sdk/software-distribution).
- [OpenCV camera calibration tutorial](https://docs.opencv.org/4.12.0/dc/dbb/tutorial_py_calibration.html).
