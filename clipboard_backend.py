"""
Cross-platform clipboard reading backend.

Ported from the standalone ComfyUI-Clipboard-Workflow-Automator script
(clipboard.py): Windows via win32clipboard + PIL.ImageGrab, Linux via
GTK/GDK (PyGObject). Detected once at import time.
"""

import io
import platform
import hashlib

from PIL import Image

_PLATFORM = platform.system()  # "Windows" or "Linux"

if _PLATFORM == "Windows":
    import win32clipboard
    from PIL import ImageGrab

elif _PLATFORM == "Linux":
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GdkPixbuf
else:
    raise RuntimeError(
        f"ComfyUI-Clipboard-Nodes: unsupported platform '{_PLATFORM}'. "
        "Only Windows and Linux are supported."
    )


def _read_image_windows():
    img = ImageGrab.grabclipboard()
    if isinstance(img, Image.Image):
        return img
    return None


def _read_text_windows():
    try:
        win32clipboard.OpenClipboard()
        try:
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                return data if data else None
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return None
    return None


def _gtk_clipboard():
    return Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)


def _read_image_linux():
    cb = _gtk_clipboard()
    pixbuf = cb.wait_for_image()
    if pixbuf is None:
        return None
    data = pixbuf.get_pixels()
    w, h = pixbuf.get_width(), pixbuf.get_height()
    stride = pixbuf.get_rowstride()
    channels = pixbuf.get_n_channels()
    mode = "RGBA" if channels == 4 else "RGB"
    img = Image.frombuffer(mode, (w, h), data, "raw", mode, stride, 1)
    return img.convert("RGB") if mode == "RGBA" and "A" not in img.getbands() else img


def _read_text_linux():
    cb = _gtk_clipboard()
    text = cb.wait_for_text()
    return text if text else None


def read_clipboard_image():
    """Return a PIL.Image if the clipboard currently holds an image, else None."""
    try:
        if _PLATFORM == "Windows":
            return _read_image_windows()
        return _read_image_linux()
    except Exception:
        return None


def read_clipboard_text():
    """Return a str if the clipboard currently holds text, else None."""
    try:
        if _PLATFORM == "Windows":
            return _read_text_windows()
        return _read_text_linux()
    except Exception:
        return None


def hash_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return hashlib.md5(buf.getvalue()).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()
