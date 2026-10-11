@echo off
rem ===========================================================================
rem  Double-click this file to start RSAC.
rem
rem  It runs the application from whichever folder this file sits in, so the
rem  project can be moved anywhere. Python 3.11 or later must be installed,
rem  along with the packages listed in requirements.txt.
rem ===========================================================================

cd /d "%~dp0"

python RSAC_Freeware_1_00.py

if errorlevel 1 (
    echo.
    echo ---------------------------------------------------------------
    echo  RSAC closed with an error. The message above explains why.
    echo.
    echo  If it says "No module named ...", the required packages are
    echo  not installed yet. Open a command prompt in this folder and run:
    echo.
    echo      python -m pip install -r requirements.txt
    echo ---------------------------------------------------------------
    echo.
    pause
)
