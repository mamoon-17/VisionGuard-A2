"""Capture a real Windows console running a supplied evidence script."""
import argparse
import ctypes
import subprocess
import time
from pathlib import Path

from PIL import Image


def window_pixels(handle):
    """Read the console's own pixels even when another app covers the window."""
    from ctypes import wintypes
    user32, gdi32=ctypes.windll.user32,ctypes.windll.gdi32
    user32.GetWindowDC.restype=wintypes.HDC
    gdi32.CreateCompatibleDC.restype=wintypes.HDC
    gdi32.CreateCompatibleBitmap.restype=wintypes.HBITMAP
    gdi32.SelectObject.restype=wintypes.HGDIOBJ
    gdi32.CreateCompatibleDC.argtypes=[wintypes.HDC]
    gdi32.CreateCompatibleBitmap.argtypes=[wintypes.HDC,ctypes.c_int,ctypes.c_int]
    gdi32.SelectObject.argtypes=[wintypes.HDC,wintypes.HGDIOBJ]
    user32.PrintWindow.argtypes=[wintypes.HWND,wintypes.HDC,wintypes.UINT]
    rectangle=wintypes.RECT()
    user32.GetWindowRect(handle,ctypes.byref(rectangle))
    width,height=rectangle.right-rectangle.left,rectangle.bottom-rectangle.top
    source=user32.GetWindowDC(handle)
    target=gdi32.CreateCompatibleDC(source)
    bitmap=gdi32.CreateCompatibleBitmap(source,width,height)
    previous=gdi32.SelectObject(target,bitmap)
    class Header(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),
                  ('planes',wintypes.WORD),('bits',wintypes.WORD),('compression',wintypes.DWORD),
                  ('image_size',wintypes.DWORD),('xppm',wintypes.LONG),('yppm',wintypes.LONG),
                  ('used',wintypes.DWORD),('important',wintypes.DWORD)]
    header=Header(ctypes.sizeof(Header),width,-height,1,32,0,0,0,0,0,0)
    pixels=ctypes.create_string_buffer(width*height*4)
    try:
        if not user32.PrintWindow(handle,target,2):
            raise RuntimeError('Native window pixel capture failed')
        gdi32.GetDIBits.argtypes=[wintypes.HDC,wintypes.HBITMAP,wintypes.UINT,wintypes.UINT,
                                 ctypes.c_void_p,ctypes.c_void_p,wintypes.UINT]
        if not gdi32.GetDIBits(target,bitmap,0,height,pixels,ctypes.byref(header),0):
            raise RuntimeError('Native bitmap read failed')
        return Image.frombuffer('RGB',(width,height),pixels.raw,'raw','BGRX',0,1)
    finally:
        gdi32.SelectObject(target,previous)
        gdi32.DeleteObject.argtypes=[wintypes.HGDIOBJ];gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC.argtypes=[wintypes.HDC];gdi32.DeleteDC(target)
        user32.ReleaseDC.argtypes=[wintypes.HWND,wintypes.HDC];user32.ReleaseDC(handle,source)


def capture(script, output, title, stage_only=False):
    """Launch real PowerShell commands; capture their actual visible console pixels."""
    for suffix in (".ready", ".captured"):
        script.with_suffix(suffix).unlink(missing_ok=True)
    user32 = ctypes.windll.user32
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 4
    process = subprocess.Popen(
        [r"C:\Windows\System32\conhost.exe",
         r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
         "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        startupinfo=startup,
    )
    handle = None
    for _ in range(240):
        found = []
        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @callback_type
        def callback(hwnd, _):
            length = user32.GetWindowTextLengthW(hwnd)
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            owner=ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
            rect=(ctypes.c_long*4)()
            user32.GetWindowRect(hwnd,rect)
            if (title in buffer.value and user32.IsWindowVisible(hwnd)
                    and rect[2]-rect[0]>400 and rect[3]-rect[1]>250):
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
    if stage_only:
        print(f"Ready for native window capture: {title}",flush=True)
        process.wait(timeout=620)
        return
    time.sleep(1)
    rectangle = (ctypes.c_long * 4)()
    if not user32.GetWindowRect(handle, rectangle):
        raise RuntimeError("Unable to read the console window bounds")
    output.parent.mkdir(parents=True, exist_ok=True)
    window_pixels(handle).save(output)
    script.with_suffix(".captured").touch()
    process.wait(timeout=30)
    print(f"Real console screenshot saved: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("title")
    parser.add_argument('--stage-only',action='store_true')
    arguments = parser.parse_args()
    capture(arguments.script.resolve(), arguments.output.resolve(), arguments.title,arguments.stage_only)
