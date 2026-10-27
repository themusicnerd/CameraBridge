# CameraBridge 0.3.0rc23

This development release fixes the workstation logo and restores calibration state after a page reload. It includes a local video calibration workstation. Select Open Video Calibration in the CameraBridge tray on the computer that receives video.

Choose NDI, RTSP, or USB Capture (Magewell). Capture at least 12 varied checkerboard views at a fixed lens setting. Inspect the optical solve and save tagged results to CameraBridge. Head calibration, camera numbers, receiver addresses, and output switches are preserved.

Native packages include NumPy and OpenCV. NDI requires an installed NDI runtime. RTSP and USB require an external FFmpeg executable. Read docs/video-calibration.md for setup.

The optical solve covers pinhole intrinsics and five OpenCV distortion coefficients. Nodal offset, video timing, and renderer-specific lens integration remain separate steps. The JSON export is not an Unreal Lens File asset. XPression CSV export uses solved field of view but does not convert OpenCV distortion to XPression lens-correction parameters.

Windows x64 and Linux x64 packages are included.
