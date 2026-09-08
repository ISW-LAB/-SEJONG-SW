REM SPDX-License-Identifier: MIT
@echo off
REM ============================================================
REM  Build FORECAST-SW-Equation-Library-Manager.exe
REM  - Bundles the complete FORECAST-SW source for deployment.
REM  - Requires Windows and Python 3.10 or later.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo [1/1] Building FORECAST-SW-Equation-Library-Manager.exe...
echo.

python build_updater.py %*
if errorlevel 1 (
    echo.
    echo [FAILED] See the build log above.
    echo          Confirm that Python 3.10 or later is installed.
    pause
    exit /b 1
)

echo.
echo [DONE] dist\FORECAST-SW-Equation-Library-Manager.exe created.
echo        Distribute this manager to edit, validate, and deploy
echo        species_data.json for the FORECAST-SW Assessment Application.
echo.
pause
