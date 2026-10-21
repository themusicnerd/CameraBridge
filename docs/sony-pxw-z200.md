# Sony PXW-Z200 integration status

Sony control is not implemented in this release.
The setup page can save a disabled PXW-Z200 entry with an address and camera number.
It does not transmit Sony camera commands or enable PIVOTCam for that entry.

Sony lists the PXW-Z200 in its Camera Remote SDK and Camera Remote Command compatibility lists.
The SDK contains the native libraries, model-specific API reference and sample code.
The public SDK page directs Australian users to a regional application page.
No SDK package is present in the workspace.
No Sony library is included in the CameraBridge release.

The SDK page currently lists Windows 11 for Windows SDK use.
This development computer runs Windows 10.
CameraBridge's Windows 10 tray test does not establish Sony SDK compatibility.

## Required integration work

1. Obtain the SDK and applicable model reference through Sony's access procedure.
2. Confirm PXW-Z200 firmware and supported connection methods.
3. Implement the native library adapter and capability discovery.
4. Add model-specific lens and paint controls.
5. Test independent setting readback and camera stop behaviour.
6. Test applicable PIVOTCam lens commands with the physical camera.

The PXW-Z200 is a handheld camcorder.
Do not represent it as a robotic pan/tilt head.
Only documented and tested camera capabilities can be enabled.

## References

- [Sony Camera Remote SDK](https://support.d-imaging.sony.co.jp/app/sdk/en/)
- [Sony Camera Remote Command](https://support.d-imaging.sony.co.jp/app/cameraremotecommand/en/index.html)
- [Australian access application](https://pro.sony/en_AU/digital-imaging-contact-us)
- [PXW-Z200 network functions](https://helpguide.sony.net/pro/z200nx800/v1/en/contents/network_use.html)
