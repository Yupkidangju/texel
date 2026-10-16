import ctypes
import os
import shutil
import subprocess


def read_clipboard() -> str | None:
    if os.name == "nt":
        user, kernel = ctypes.windll.user32, ctypes.windll.kernel32
        user.GetClipboardData.restype = ctypes.c_void_p
        kernel.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel.GlobalLock.restype = ctypes.c_void_p
        kernel.GlobalUnlock.argtypes = [ctypes.c_void_p]
        if not user.OpenClipboard(None):
            return None
        try:
            handle = user.GetClipboardData(13)
            if not handle:
                return None
            pointer = kernel.GlobalLock(handle)
            if not pointer:
                return None
            try:
                return ctypes.wstring_at(pointer)
            finally:
                kernel.GlobalUnlock(handle)
        finally:
            user.CloseClipboard()
    for command in (
        ["wl-paste", "--no-newline"],
        ["pbpaste"],
        ["xclip", "-selection", "clipboard", "-o"],
    ):
        if shutil.which(command[0]):
            try:
                return subprocess.check_output(command, timeout=2).decode("utf-8")
            except subprocess.SubprocessError, UnicodeError, OSError:
                pass
    return None


def write_clipboard(value: str) -> bool:
    if os.name != "nt":
        return False
    user, kernel = ctypes.windll.user32, ctypes.windll.kernel32
    kernel.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel.GlobalAlloc.restype = ctypes.c_void_p
    kernel.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel.GlobalFree.argtypes = [ctypes.c_void_p]
    user.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user.SetClipboardData.restype = ctypes.c_void_p
    data = value.encode("utf-16-le") + b"\x00\x00"
    handle = kernel.GlobalAlloc(0x42, len(data))
    if not handle:
        return False
    pointer = kernel.GlobalLock(handle)
    if not pointer:
        kernel.GlobalFree(handle)
        return False
    ctypes.memmove(pointer, data, len(data))
    kernel.GlobalUnlock(handle)
    transferred = False
    try:
        if not user.OpenClipboard(None):
            return False
        try:
            user.EmptyClipboard()
            transferred = bool(user.SetClipboardData(13, handle))
            return transferred
        finally:
            user.CloseClipboard()
    finally:
        if not transferred:
            kernel.GlobalFree(handle)
