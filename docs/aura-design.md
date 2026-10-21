# Aura operator layout

The reference direction is the flat charcoal Aura theme, not the older bevelled paint-control appearance. The local DashBoard launcher already specifies `-Ddashboard.lnf=AURA`; CameraBridge does not modify that setting.

References supplied by the operator:

- [Ross Aura tutorial](https://www.rossvideo.com/resources/ross-university/aura-theme/)
- [PTZ plugin preset layout](https://www.rossvideo.com/wp-content/uploads/2022/12/PTZ-Plugin.png.webp)
- [Older Panasonic paint panel](https://www.rossvideo.com/wp-content/uploads/2022/12/Camera-Plugins.png.webp)
- Archived Panasonic Camera Control Panel User Guide,4502DR-001-1.0, supplied as a historical workflow reference. Its archived status is retained; it is not used as the current AW-HE130 protocol authority.

The two manufacturer-specific native `.grid` files remain independent. Each has its own camera rail, identity/health strip, page navigation, session and status footer. Panasonic has PTZ, Presets, Paint, TD1C and Config pages; Marshall has Paint, Exposure, OSD and Config pages. Navigation and camera selection use purple highlights; action buttons use grey or cyan. No Ross logo is included. The artwork files are unmodified Panasonic/Marshall assets; see `dashboard/assets/SOURCES.md`.

The Panasonic PTZ page has a large eight-direction touch pad, central stop, jog speed and separate vertical iris/zoom/focus strips. It is a direction pad rather than an undocumented analogue-positioner widget. Touch movement must be explicitly enabled after login. Press/release and mouse-exit controls retain the backend's bounded jog/watchdog behaviour. The physical TouchDrive positioner is an independent integration path.

Paint controls have numeric entry and vertical or horizontal native faders. Red/blue gain on HE130 displays the operator offset -150..+150 while retaining native wire values0..300. Actual readback state/age remains separate from the draft control value. Mode dependencies still apply. Unsupported paint families are not represented as functioning controls.

The preset page has 20 large shot buttons, persistent names and one-shot overwrite protection. Selecting another camera waits for the previous stop request to succeed before changing targets. Lab-only Preset/Program selection inputs live on the TD1C page and are explicitly labelled as simulator events.

The layout uses a 1366×800 virtual canvas and documented native OGLML tabs, reveal buttons, faders and images. Geometry tests check element bounds; script/API tests check every expected label ID. Native feedback callbacks have also passed in DashBoard 9.15.2 after the redesign. Screenshot/touch/visual acceptance still requires a working capture path or an operator check; no pixel-perfect native render is claimed.

The generator writes fully qualified local logo URLs. After moving the directory or deploying to Linux, run `python dashboard/build_panels.py` before opening the panels so those URLs reflect the new location.
