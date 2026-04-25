# Launchers

This folder contains double-click launchers for both Windows and Ubuntu/Linux.

## Windows

Use the `.bat` files:

- `set-up-app.bat`
- `launch-app.bat`
- `stop-app.bat`
- `update-app.bat`

They look for GNU Make in `PATH` under one of these names:

- `make`
- `mingw32-make`
- `gmake`

## Ubuntu / Linux

Use the `.desktop` files:

- `set-up-app.desktop`
- `launch-app.desktop`
- `stop-app.desktop`
- `update-app.desktop`

They open a terminal and run the matching shell script.

Depending on the desktop environment, the first use may require:

1. Marking the `.desktop` file as executable.
2. Choosing `Allow Launching` in the file manager.

The `.sh` scripts remain available for terminal usage too.

## Update targets

- `make update-repo`: runs exactly `git pull origin main`
- `make update`: runs `make update-repo` and then reinstalls the project dependencies

The launcher files named `update-app.*` use `make update`.
