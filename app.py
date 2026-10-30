"""Browser Use AI Studio — Main Application Entrypoint (PyWebView Desktop + Web Server Fallback)."""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


# Ensure Windows uses ProactorEventLoop so browser-use can spawn Chrome/Edge subprocesses cleanly
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass


def _find_free_port(preferred: int = 8765) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", preferred)) != 0:
            return preferred
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    check_host = "127.0.0.1" if host == "0.0.0.0" else host
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            if s.connect_ex((check_host, port)) == 0:
                return True
        time.sleep(0.15)
    return False


class PyWebViewBridge:
    """Native desktop bridge exposed to JavaScript inside PyWebView as window.pywebview.api."""

    def __init__(self) -> None:
        self._window = None

    def attach_window(self, window) -> None:
        self._window = window

    def is_desktop(self) -> bool:
        return True

    def open_external_url(self, url: str) -> bool:
        if url and url.startswith(("http://", "https://")):
            webbrowser.open(url)
            return True
        return False

    def pick_browser_exe(self) -> str:
        import webview

        if not self._window:
            return ""
        file_types = ("Executable Files (*.exe)", "All files (*.*)") if sys.platform == "win32" else ("All files (*.*)",)
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result and len(result) > 0:
            return str(result[0])
        return ""

    def pick_folder(self) -> str:
        import webview

        if not self._window:
            return ""
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            return str(result[0])
        return ""

    def save_text_file(self, content: str, default_filename: str = "browser_use_result.md") -> str:
        import webview

        if not self._window:
            return ""
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=default_filename,
        )
        if result:
            target = Path(result[0] if isinstance(result, (list, tuple)) else result)
            target.write_text(content or "", encoding="utf-8")
            return str(target)
        return ""


def _run_uvicorn_in_thread(host: str, port: int) -> uvicorn.Server:
    from backend.server import app

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    def _target() -> None:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    thread = threading.Thread(target=_target, name="BrowserUseStudioServer", daemon=True)
    thread.start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser Use AI Studio — رابط گرافیکی فارسی Browser Use")
    parser.add_argument("--web", action="store_true", help="اجرا در حالت سرور وب (مرورگر) به جای پنجره دسکتاپ pywebview")
    parser.add_argument("--no-open", action="store_true", help="عدم باز کردن خودکار مرورگر در حالت --web")
    parser.add_argument("--host", default="127.0.0.1", help="آدرس هاست سرور (پیش‌فرض: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="پورت سرور (0 = انتخاب خودکار پورت آزاد)")
    args = parser.parse_args()

    if args.web:
        port = args.port or _find_free_port(8765)
        url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{port}"
        print(f"\n🚀 استودیو Browser Use در حالت وب راه‌اندازی شد: {url}\n")
        if not args.no_open and args.host in ("127.0.0.1", "localhost"):
            threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        from backend.server import app

        uvicorn.run(app, host=args.host, port=port, log_level="info", loop="asyncio")
        return

    # Default mode: Native Desktop Window via PyWebView
    port = args.port or _find_free_port(8765)
    server = _run_uvicorn_in_thread("127.0.0.1", port)
    if not _wait_for_server("127.0.0.1", port, timeout=20.0):
        print("❌ خطا: سرور داخلی برنامه نتوانست راه‌اندازی شود.")
        sys.exit(1)

    url = f"http://127.0.0.1:{port}"
    try:
        import webview

        bridge = PyWebViewBridge()
        window = webview.create_window(
            title="Browser Use AI Studio — دستیار هوشمند مرورگر",
            url=url,
            js_api=bridge,
            width=1380,
            height=880,
            min_size=(1020, 660),
            background_color="#090d16",
            text_select=True,
        )
        bridge.attach_window(window)
        webview.start(debug=False)
        server.should_exit = True
    except Exception as exc:
        print(f"⚠️ پنجره دسکتاپ PyWebView باز نشد ({exc}).")
        print(f"🌐 در حال باز کردن رابط کاربری در مرورگر پیش‌فرض شما: {url}")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.should_exit = True


if __name__ == "__main__":
    main()
