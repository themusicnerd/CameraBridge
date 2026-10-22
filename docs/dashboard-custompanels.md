# Native DashBoard panels

The project generates a unified CameraBridge OGLML grid file and separate manufacturer panels.
They use native controls and ogScript.
They do not embed the web interface.
Use [the unified panel](unified-dashboard.md) for camera setup and camera controls in one file.
Open CameraBridge asks the operating system to open the configured HTTP or HTTPS address.

The panel keeps its token in memory.
It sends commands through authenticated HTTP requests.
A 200-millisecond timer sends at most one queued paint parameter per tick.
Panel state polling uses the central backend state.

The backend confirmation line is separate from the editable control.
Feedback updates do not generate user writes.
Unavailable or mode-dependent parameters are read-only.
The panel stops the previous camera before a selection change.
Closing the panel attempts a stop.

## Generate panels from source

1. Run `python dashboard/build_panels.py` from the repository.
2. Open the generated grid files in DashBoard.
3. Check native feedback and each page.

For a release package, use `CameraBridge-cli panels --output PATH` instead.
That command sets image paths for the selected output directory.
For a TouchDrive, use the panel host to replace local image paths with HTTP paths.

The source files are `dashboard/SW-Panasonic-Camera-Control.grid` and `dashboard/SW-Marshall-Camera-Control.grid`.
The generator is the source of layout changes.
Do not edit only generated files.

See [operation](operation.md) for controls and [native validation](native-dashboard-validation.md) for evidence.
