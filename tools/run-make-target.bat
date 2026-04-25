@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "REPO_DIR=%SCRIPT_DIR%.."
set "TARGET=%~1"
set "ACTION_LABEL=%~2"
set "EXIT_CODE=0"

if "%TARGET%"=="" (
    echo Usage: %~nx0 ^<make-target^> [label]
    set "EXIT_CODE=1"
    goto :finish
)

if "%ACTION_LABEL%"=="" set "ACTION_LABEL=%TARGET%"

call :resolve_make
if errorlevel 1 goto :finish

pushd "%REPO_DIR%" >nul 2>&1
if errorlevel 1 (
    echo Could not open repository root: "%REPO_DIR%"
    set "EXIT_CODE=1"
    goto :finish
)

echo %ACTION_LABEL%...
%MAKE_CMD% %TARGET%
set "EXIT_CODE=%ERRORLEVEL%"

popd >nul 2>&1

:finish
echo.
if "%EXIT_CODE%"=="0" (
    echo Finished successfully.
) else (
    echo The command failed with exit code %EXIT_CODE%.
)
echo.
pause
exit /b %EXIT_CODE%

:resolve_make
where /Q make.exe
if not errorlevel 1 (
    set "MAKE_CMD=make"
    exit /b 0
)

where /Q mingw32-make.exe
if not errorlevel 1 (
    set "MAKE_CMD=mingw32-make"
    exit /b 0
)

where /Q gmake.exe
if not errorlevel 1 (
    set "MAKE_CMD=gmake"
    exit /b 0
)

echo GNU Make was not found in PATH.
echo Install it and try again. Supported command names: make, mingw32-make or gmake.
set "EXIT_CODE=127"
exit /b 1
