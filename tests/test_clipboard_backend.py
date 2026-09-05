import io

import pytest
from PIL import Image

import clipboard_backend as cb


# ---------------------------------------------------------------------------
# Pure functions — no clipboard access involved
# ---------------------------------------------------------------------------

def _make_image(color=(255, 0, 0), size=(4, 4)):
    return Image.new("RGB", size, color)


def test_hash_image_stable_for_identical_content():
    img_a = _make_image()
    img_b = _make_image()
    assert cb.hash_image(img_a) == cb.hash_image(img_b)


def test_hash_image_differs_for_different_content():
    red = _make_image(color=(255, 0, 0))
    blue = _make_image(color=(0, 0, 255))
    assert cb.hash_image(red) != cb.hash_image(blue)


def test_hash_text_stable_and_distinct():
    assert cb.hash_text("hello") == cb.hash_text("hello")
    assert cb.hash_text("hello") != cb.hash_text("world")


def test_hash_text_handles_unicode():
    # md5 over utf-8 bytes should not raise for non-ASCII input
    assert cb.hash_text("žluťoučký kůň") == cb.hash_text("žluťoučký kůň")


# ---------------------------------------------------------------------------
# Dispatch logic: read_clipboard_image / read_clipboard_text
#
# These monkeypatch the private per-platform functions directly, so the
# tests exercise the dispatch + exception-swallowing behavior without
# needing a real Windows or Linux clipboard backend available.
# ---------------------------------------------------------------------------

@pytest.fixture
def force_platform(monkeypatch):
    def _force(name):
        monkeypatch.setattr(cb, "_PLATFORM", name)
    return _force


def test_read_clipboard_image_windows_dispatch(monkeypatch, force_platform):
    force_platform("Windows")
    sentinel = _make_image()
    monkeypatch.setattr(cb, "_read_image_windows", lambda: sentinel)
    assert cb.read_clipboard_image() is sentinel


def test_read_clipboard_image_linux_dispatch(monkeypatch, force_platform):
    force_platform("Linux")
    sentinel = _make_image()
    monkeypatch.setattr(cb, "_read_image_linux", lambda: sentinel)
    assert cb.read_clipboard_image() is sentinel


def test_read_clipboard_text_windows_dispatch(monkeypatch, force_platform):
    force_platform("Windows")
    monkeypatch.setattr(cb, "_read_text_windows", lambda: "copied text")
    assert cb.read_clipboard_text() == "copied text"


def test_read_clipboard_text_linux_dispatch(monkeypatch, force_platform):
    force_platform("Linux")
    monkeypatch.setattr(cb, "_read_text_linux", lambda: "copied text")
    assert cb.read_clipboard_text() == "copied text"


def test_read_clipboard_image_swallows_backend_errors(monkeypatch, force_platform):
    force_platform("Linux")

    def _boom():
        raise RuntimeError("clipboard backend blew up")

    monkeypatch.setattr(cb, "_read_image_linux", _boom)
    # Should not raise — read_clipboard_image() treats backend errors as
    # "nothing on the clipboard right now" rather than a hard failure.
    assert cb.read_clipboard_image() is None


def test_read_clipboard_text_swallows_backend_errors(monkeypatch, force_platform):
    force_platform("Linux")

    def _boom():
        raise RuntimeError("clipboard backend blew up")

    monkeypatch.setattr(cb, "_read_text_linux", _boom)
    assert cb.read_clipboard_text() is None


def test_read_clipboard_image_returns_none_when_nothing_copied(monkeypatch, force_platform):
    force_platform("Linux")
    monkeypatch.setattr(cb, "_read_image_linux", lambda: None)
    assert cb.read_clipboard_image() is None
