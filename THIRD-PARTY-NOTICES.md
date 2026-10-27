# Third-party notices

CameraBridge packages contain third-party software.
The project does not change the rights of those software owners.

| Component | Reference |
|---|---|
| Qt for Python, PySide6 Essentials and Shiboken | [Qt for Python licenses](https://doc.qt.io/qtforpython-6/licenses.html) |
| Python | [Python license](https://docs.python.org/3/license.html) |
| PyInstaller bootloader | [License and bootloader exception](https://pyinstaller.org/en/stable/license.html) |
| OpenSSL, when included by Python | [OpenSSL license](https://openssl-library.org/source/license/) |
| SQLite, when included by Python | [SQLite copyright](https://sqlite.org/copyright.html) |
| Panasonic image | Manufacturer identification image; Panasonic owns the applicable rights |
| Ross identification image | Ross Video owns the applicable rights |
| Marshall image | Manufacturer identification image; Marshall owns the applicable rights |

The package includes dynamically loaded Qt and Shiboken libraries under their applicable licenses.
The licenses directory contains the license texts supplied by their Python distributions.
Qt for Python offers LGPLv3, GPLv3 and commercial license options.
The build uses the LGPLv3 option for the included Essentials components.
Users can replace the separate Qt libraries with compatible versions.
The [Qt source archive](https://download.qt.io/official_releases/QtForPython/) supplies the corresponding upstream source packages.

The package does not include Ross DashBoard or camera manufacturer applications.
Ross, Panasonic and Marshall do not endorse this project.
The repository owner has not selected a distribution license for the CameraBridge source.
No CameraBridge source license is implied by this release.

## Sony Camera Remote SDK 2.02.00

Windows and Linux packages include Sony libraries with the CameraBridge adapter.
The SDK remains Sony's licensed software.
Read `SONY-SDK-LICENSE.txt` in the bundled `sony` directory.
Camera access setup requires acknowledgement of the SDK terms and camera warranty conditions.
Sony does not develop or support CameraBridge.
CameraBridge does not grant rights beyond the applicable Sony license.
The bundled open source notices cover libssh2, libusb and OpenSSL.
Sony's original SDK download includes the corresponding open source archives.
See [Sony's SDK license and downloads](https://support.d-imaging.sony.co.jp/app/sdk/licenseagreement_d/en-US.html).

## Bitfocus Panasonic catalog

The Panasonic model names and family grouping derive from the Bitfocus Panasonic camera module.
The module uses the MIT license, copyright 2018 Bitfocus AS.
Read the [included license](docs/third-party/bitfocus-panasonic-MIT.txt).
CameraBridge implements its own Python transport and control logic.
The reference project is [companion-module-panasonic-ptz](https://github.com/bitfocus/companion-module-panasonic-ptz).
## Video calibration components

Native packages include NumPy and OpenCV Python wheels.
Their license files and included-component notices are copied to the package `licenses` directory.
OpenCV wheel notices include the third-party components supplied in that wheel.

The NDI receive integration uses the installed NDI runtime.
CameraBridge does not include NDI runtime binaries or SDK files.
Install the applicable runtime from the NDI provider.

RTSP and USB capture use a separately installed FFmpeg executable.
CameraBridge does not redistribute that executable.
The selected FFmpeg build remains subject to its own license terms.
