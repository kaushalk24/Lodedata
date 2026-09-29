# The Design Assistant as a Windows program

`LodeData.exe` is the same app in a window of its own. It needs no server,
no internet and no Python: everything it needs is in its folder.

## Get it

Every push to the branch is built and checked on a Windows machine by
GitHub (`.github/workflows/windows-exe.yml`) and published as the
"windows-latest" release:

https://github.com/kaushalk24/Lodedata/releases/download/windows-latest/LodeData-windows.zip

(sign in to GitHub first if the repository is private; the build is also
under the repository's Actions tab, as the run's LodeData-windows artifact).

## Use it

1. Unzip `LodeData-windows.zip` anywhere, e.g. `C:\LodeData` or a shared drive.
2. Open the `LodeData` folder and double-click `LodeData.exe`. Keep the
   folder together — the `.exe` needs the `_internal` folder beside it.
   Right-click → Send to → Desktop (create shortcut) for a desktop icon.
3. The first time, Windows may say "Windows protected your PC" (the program
   is not signed): **More info → Run anyway**.

Windows 10 or 11, 64-bit. The window is Edge's WebView2, which Windows 11
already has.

* **File → Open / Save Network** use Windows' own dialogs; Save writes
  straight back into the `.ntw` it was opened from, as Lode Data does.
* The networks opened are kept for each Windows user in
  `%LOCALAPPDATA%\LodeData` (`designs.db`), so they are there next time.
  Nothing is shared with other PCs.
* A new version: replace the `LodeData` folder with the new one. The
  networks in `%LOCALAPPDATA%\LodeData` stay.
* If it does not start: `%LOCALAPPDATA%\LodeData\lodedata.log` says why.

## Build it yourself (optional)

On a Windows PC with Python 3.10 or newer: `desktop\build.bat`. It installs
what it needs, builds `dist\LodeData\LodeData.exe` and checks it
(`LodeData.exe --check` starts the engine, saves and reopens a network
through it, and exits 0).

How it works: `desktop/lodedata_desktop.py` runs the app's engine inside the
program on this PC only (127.0.0.1, port 17170, not reachable from the
network) and shows the page in a pywebview window; the page's Open/Save go
to Windows' dialogs through `window.pywebview.api` (`app/web/app.js`,
`desktopFile`).
