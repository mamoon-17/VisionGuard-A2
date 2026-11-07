"""Capture a real Windows console running a supplied evidence script."""
import argparse
import ctypes
import subprocess
import time
from pathlib import Path

from PIL import ImageGrab


def capture(script, output, title):
    """Launch real PowerShell commands; capture their actual visible console pixels."""
    user32 = ctypes.windll.user32
    process = subprocess.Popen(
        [r"C:\Windows\System32\conhost.exe",
         r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
         "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    handle = None
    for _ in range(60):
        found = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @callback_type
        def callback(hwnd, _):
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if title in buffer.value and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
            return True

        user32.EnumWindows(callback, 0)
        if found and script.with_suffix(".ready").exists():
            handle = found[0]
            break
        if process.poll() is not None:
            raise RuntimeError("The evidence console exited before it was ready")
        time.sleep(0.5)
    if not handle:
        raise RuntimeError("No ready evidence console was found; no screenshot was created")
    time.sleep(1)
    rectangle = (ctypes.c_long * 4)()
    if not user32.GetWindowRect(handle, rectangle):
        raise RuntimeError("Unable to read the console window bounds")
    output.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=tuple(rectangle), all_screens=True).save(output)
    script.with_suffix(".captured").touch()
    process.wait(timeout=30)
    print(f"Real console screenshot saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("title")
    arguments = parser.parse_args()
    capture(arguments.script.resolve(), arguments.output.resolve(), arguments.title)
