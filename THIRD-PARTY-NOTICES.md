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
