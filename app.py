import sys
import threading
import webbrowser
import logging
import uvicorn
from pathlib import Path

logger = logging.getLogger(__name__)
SERVER_PORT = 8000

try:
    import pystray
    from PIL import Image
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


class DesktopApp:

    def __init__(self):
        self._server_thread = None
        self._tray_icon = None
        self._running = False

    def start_server(self):
        from main import app
        config = uvicorn.Config(app, host="127.0.0.1", port=SERVER_PORT, log_level="warning")
        server = uvicorn.Server(config)
        server.run()

    def open_browser(self):
        webbrowser.open(f"http://127.0.0.1:{SERVER_PORT}")

    def on_quit(self, icon=None, item=None):
        self._running = False
        if self._tray_icon:
            self._tray_icon.stop()
        sys.exit(0)

    def run(self):
        self._running = True

        self._server_thread = threading.Thread(target=self.start_server, daemon=True)
        self._server_thread.start()

        import time
        time.sleep(2)
        self.open_browser()

        if HAS_TRAY:
            img = Image.new("RGB", (64, 64), (56, 189, 248))
            menu = pystray.Menu(
                pystray.MenuItem("Paneli Aç", self.open_browser),
                pystray.MenuItem("Çıkış", self.on_quit),
            )
            self._tray_icon = pystray.Icon("voip_service", img, "SMS VoIP Servisi", menu)
            self._tray_icon.run()
        else:
            while self._running:
                try:
                    import time as t
                    t.sleep(1)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = DesktopApp()
    app.run()
