@echo off
title Mental Omega Arsenal Launcher

:menu
cls
echo =====================================
echo    Mental Omega Arsenal Launcher
echo =====================================
echo.
echo 1. Launch UI Version 1 (mental_omega_arsenal.py)
echo 2. Launch UI Version 2 (mental_omega_arsenal_layout2.py)
echo 3. Exit
echo.
set /p choice="Please select an option (1-3): "

if "%choice%"=="1" goto launch_ui1
if "%choice%"=="2" goto launch_ui2
if "%choice%"=="3" goto exit
goto invalid_choice

:launch_ui1
echo.
echo Launching Mental Omega Arsenal - Version 1...
python mental_omega_arsenal.py
echo.
echo Application closed.
pause
goto menu

:launch_ui2
echo.
echo Launching Mental Omega Arsenal - Version 2...
python mental_omega_arsenal_layout2.py
echo.
echo Application closed.
pause
goto menu

:invalid_choice
echo.
echo Invalid choice. Please select 1, 2, or 3.
pause
goto menu

:exit
echo.
echo Goodbye!
timeout /t 2 >nul
exit