@echo off
echo SMS Receiver - Tek EXE Build
echo ==============================
echo.

pip install -r requirements.txt
pip install pyinstaller 2>nul

pyinstaller --onefile --windowed --name "SMSReceiver" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "aiohttp" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    --hidden-import "sqlite3" ^
    --collect-all "fastapi" ^
    --collect-all "uvicorn" ^
    --collect-all "jinja2" ^
    app.py

echo.
copy /Y "dist\SMSReceiver.exe" "%USERPROFILE%\Desktop\SMSReceiver.exe" >nul
echo SMSReceiver.exe masaustune kopyalandi!
echo.

rd /s /q build 2>nul
del SMSReceiver.spec 2>nul

echo Build tamam! dist\SMSReceiver.exe ve masaustunde.
pause
