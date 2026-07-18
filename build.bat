@echo off
title SMS Receiver Build
echo SMS Receiver - Tek EXE Build (CustomTkinter)
echo =============================================
echo.

pip install -r requirements.txt
pip install pyinstaller 2>nul

pyinstaller --onefile --windowed --name "SMSReceiver" ^
    --hidden-import "aiohttp" ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "sqlite3" ^
    --collect-all "customtkinter" ^
    app_ctk.py

if %ERRORLEVEL% NEQ 0 (
    echo Build HATASI!
    pause
    exit /b 1
)

echo.
copy /Y "dist\SMSReceiver.exe" "%USERPROFILE%\Desktop\SMSReceiver.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo SMSReceiver.exe masaustune kopyalandi!
) else (
    echo Kopyalama hatasi
)

rd /s /q build 2>nul
del SMSReceiver.spec 2>nul

echo.
echo Build tamam! dist\SMSReceiver.exe ve masaustunde.
pause
