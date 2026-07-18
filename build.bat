@echo off
echo Building SMS Receiver Desktop App...
echo.

pip install -r requirements.txt
pip install pyinstaller

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "SMSReceiver" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "aiohttp" ^
    --hidden-import "pystray" ^
    --hidden-import "PIL" ^
    --collect-all "fastapi" ^
    --collect-all "uvicorn" ^
    --collect-all "jinja2" ^
    app.py

echo.
echo Build complete! Look for SMSReceiver.exe in the dist folder.
pause
