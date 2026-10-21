# Release engineering

## Package contents

Each package contains desktop and console programs, Python, Qt libraries, web assets, panel templates, configuration and documentation.
Keep the `_internal` directory with the executable.
Private runtime files are not build inputs.

| Target | Runner | Archive |
|---|---|---|
| Windows x64 | `windows-2022` | ZIP |
| Linux x64 | `ubuntu-22.04` | TAR.GZ |
| macOS Intel | `macos-15-intel` | TAR.GZ |
| macOS Apple silicon | `macos-15` | TAR.GZ |

Each archive has a separate SHA256 file.
BUILD.json records the target, Python version and build system.
The packages have no publisher signature or production hardware approval.
The macOS bootloader can have a local ad-hoc signature from the build tool.
That signature is not an Apple Developer ID signature or notarization.

## Build locally

1. Use the target operating system and processor.
2. Install Python 3.11.
3. Create and activate a build virtual environment.
4. Install requirements-build.txt and requirements-desktop.txt with pip.
5. Run `python dashboard/build_panels.py`.
6. Run `python -m unittest discover -v`.
7. Run `python tools/check_docs.py`.
8. Run `python tools/smoke_tray.py`.
9. Run `python tools/build_release.py --target TARGET`.
10. Run `python tools/smoke_release.py EXECUTABLE`.

Replace TARGET with a table target.
Replace EXECUTABLE with `build/package/CameraBridge/CameraBridge-cli`, or its `.exe` path on Windows.
The build tool is pinned in requirements-build.txt.
PyInstaller does not compile another operating system's executable.

## Publish

1. Check that the repository contains no runtime credentials or secrets.
2. Update pyproject.toml, the change record and release notes.
3. Commit and push the reviewed source.
4. Create the matching version tag.
5. Push the tag.
6. Check all four build jobs and the release job.

The workflow publishes a development prerelease only after all four build jobs pass.
Each build job runs source tests, a desktop lifecycle test and a packaged-program test.
The desktop test checks close-to-tray, reopening, port changes and graceful process shutdown.
The package test checks account creation, panel export, web assets, login, CGI readback and clean shutdown.
The workflow uploads tested packages directly to a draft release.
It does not require GitHub Actions artifact storage.
The release remains a draft until all four platform jobs pass.
For a manual release run, select an existing version tag.

The private repository uses the account's GitHub Actions allowance.
Build success does not establish physical camera acceptance.

## References

- [PyInstaller runtime paths](https://pyinstaller.org/en/stable/runtime-information.html)
- [PyInstaller build instructions](https://pyinstaller.org/en/stable/usage.html)
- [GitHub runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
