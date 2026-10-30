"""System & Browser Diagnostics (System Doctor) for Browser Use AI Studio."""

from __future__ import annotations

import glob
import importlib.metadata
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any


def _expand_win_path(pattern: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(pattern))
    return expanded


def detect_installed_browsers() -> list[dict[str, str]]:
    """Detect all installed Chromium-based browsers across Windows, macOS, and Linux."""
    system = platform.system()
    candidates: list[tuple[str, str, str]] = []
    pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")

    if system == "Windows":
        pw_dir = pw_path or r"%LOCALAPPDATA%\ms-playwright"
        candidates = [
            ("chrome", "Google Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            ("chrome", "Google Chrome (x86)", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ("chrome", "Google Chrome (User)", r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            ("msedge", "Microsoft Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            ("msedge", "Microsoft Edge (x64)", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            ("msedge", "Microsoft Edge (User)", r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            ("brave", "Brave Browser", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ("brave", "Brave Browser (x86)", r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ("brave", "Brave Browser (User)", r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
            ("chromium", "Playwright Chromium", rf"{pw_dir}\chromium-*\chrome-win*\chrome.exe"),
            ("chromium", "Chromium", r"C:\Program Files\Chromium\Application\chrome.exe"),
            ("chromium", "Chromium (User)", r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
        ]
    elif system == "Darwin":
        pw_dir = pw_path or "~/Library/Caches/ms-playwright"
        candidates = [
            ("chrome", "Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ("msedge", "Microsoft Edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            ("brave", "Brave Browser", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            ("chromium", "Chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
            ("chromium", "Playwright Chromium", f"{pw_dir}/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:
        pw_dir = pw_path or "~/.cache/ms-playwright"
        candidates = [
            ("chrome", "Google Chrome", "/usr/bin/google-chrome-stable"),
            ("chrome", "Google Chrome", "/usr/bin/google-chrome"),
            ("chromium", "Chromium", "/usr/bin/chromium"),
            ("chromium", "Chromium Browser", "/usr/bin/chromium-browser"),
            ("msedge", "Microsoft Edge", "/usr/bin/microsoft-edge-stable"),
            ("brave", "Brave Browser", "/usr/bin/brave-browser"),
            ("chromium", "Playwright Chromium", f"{pw_dir}/chromium-*/chrome-linux*/chrome"),
        ]

    found: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    for b_id, label, raw_pattern in candidates:
        expanded = _expand_win_path(raw_pattern)
        matches = sorted(glob.glob(expanded), reverse=True) if "*" in expanded else ([expanded] if Path(expanded).is_file() else [])
        for m in matches:
            norm = str(Path(m))
            if norm not in seen_paths and Path(norm).is_file():
                seen_paths.add(norm)
                found.append({"id": b_id, "name": label, "path": norm})

    # Also check PATH on Linux/macOS
    if system != "Windows":
        for cmd, b_id, label in [
            ("google-chrome", "chrome", "Google Chrome"),
            ("chromium", "chromium", "Chromium"),
            ("chromium-browser", "chromium", "Chromium Browser"),
            ("microsoft-edge", "msedge", "Microsoft Edge"),
            ("brave-browser", "brave", "Brave Browser"),
        ]:
            which_path = shutil.which(cmd)
            if which_path and which_path not in seen_paths:
                seen_paths.add(which_path)
                found.append({"id": b_id, "name": label, "path": which_path})

    return found


def resolve_browser_executable(channel_choice: str, custom_path: str = "") -> tuple[str | None, str | None]:
    """Return (channel_enum_str_or_None, executable_path_or_None) for BrowserProfile."""
    if channel_choice == "custom" and custom_path.strip():
        return None, custom_path.strip()

    browsers = detect_installed_browsers()
    if channel_choice in ("chrome", "msedge", "brave", "chromium"):
        for b in browsers:
            if b["id"] == channel_choice:
                return (channel_choice if channel_choice in ("chrome", "msedge", "chromium") else None), b["path"]
        if channel_choice in ("chrome", "msedge", "chromium"):
            return channel_choice, None

    # auto: prefer Chrome -> Edge -> Brave -> Chromium
    for pref in ("chrome", "msedge", "brave", "chromium"):
        for b in browsers:
            if b["id"] == pref:
                return (pref if pref in ("chrome", "msedge", "chromium") else None), b["path"]

    return None, None


def has_gui_display() -> bool:
    system = platform.system()
    if system in ("Windows", "Darwin"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def get_default_chrome_user_data_hint() -> str:
    system = platform.system()
    if system == "Windows":
        local_app = os.environ.get("LOCALAPPDATA", r"C:\Users\YourName\AppData\Local")
        return str(Path(local_app) / "Google" / "Chrome" / "User Data")
    if system == "Darwin":
        return str(Path.home() / "Library" / "Application Support" / "Google" / "Chrome")
    return str(Path.home() / ".config" / "google-chrome")


def get_system_health() -> dict[str, Any]:
    def _ver(pkg: str) -> str:
        try:
            return importlib.metadata.version(pkg)
        except Exception:
            return "نامشخص"

    browsers = detect_installed_browsers()
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "python_version": sys.version.split()[0],
        "browser_use_version": _ver("browser-use"),
        "pywebview_version": _ver("pywebview"),
        "has_display": has_gui_display(),
        "browsers": browsers,
        "browser_ready": len(browsers) > 0,
        "chrome_profile_hint": get_default_chrome_user_data_hint(),
    }
