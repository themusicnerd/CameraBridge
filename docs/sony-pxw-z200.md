# Sony PXW-Z200 integration status

Sony control is not implemented in this release.
The setup page can save a disabled PXW-Z200 entry with an address and camera number.
It does not transmit Sony camera commands or enable PIVOTCam for that entry.

Sony lists the PXW-Z200 in its Camera Remote SDK and Camera Remote Command compatibility lists.
The SDK contains the native libraries, model-specific API reference and sample code.
Camera Remote SDK 2.02.00 was downloaded from Sony on 22 October 2026.
The Windows x64 and Linux x64 packages are available in the local development workspace.
Both packages passed the published file-size check and ZIP integrity check.
Local SHA-256 checksums are recorded with the packages.
The API reference and sample archives were also extracted and checked.
The vendor packages are stored separately from this repository.
No Sony library is included in the CameraBridge release.

The included reference lists Windows 11 for Windows SDK use.
It lists Ubuntu 22.04 LTS and Ubuntu 24.04 LTS for Linux x64.
This development computer runs Windows 10.
CameraBridge's Windows 10 tray test does not establish Sony SDK compatibility.

The PXW-Z200 supports SDK remote control through wired Ethernet and wireless LAN.
The SDK reference requires SSH authentication for this model.
It does not list USB remote control for this model.
The next integration work targets Windows x64 and Linux x64.

## Required integration work

1. Review the included API and model capability tables.
2. Confirm PXW-Z200 firmware and configure camera network authentication.
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
- [Sony SDK license and downloads](https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement_d/en-US.html)
- [PXW-Z200 network functions](https://helpguide.sony.net/pro/z200nx800/v1/en/contents/network_use.html)
