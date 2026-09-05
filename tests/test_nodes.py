import pytest

from comfyui_clipboard_nodes import nodes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeImage:
    """Stand-in for a PIL.Image so we don't need real image data in tests."""

    def __init__(self, tag):
        self.tag = tag


def _queue_reader(values):
    """Returns a callable that yields successive values from `values`,
    then keeps returning the last one forever (mirrors polling a clipboard
    that stops changing)."""
    values = list(values)

    def _read():
        if values:
            return values.pop(0)
        return None

    return _read


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    # Never actually sleep in tests.
    monkeypatch.setattr(nodes.time, "sleep", lambda _seconds: None)


@pytest.fixture
def fake_pil_conversion(monkeypatch):
    # Bypass real tensor conversion; ClipboardImageInput just needs
    # _pil_to_tensor to be callable and return a (tensor, mask) pair.
    monkeypatch.setattr(nodes, "_pil_to_tensor", lambda img: (img, "mask"))


# ---------------------------------------------------------------------------
# ClipboardImageInput
# ---------------------------------------------------------------------------

def test_image_node_ignores_preexisting_clipboard_content(monkeypatch, fake_pil_conversion):
    old_img = FakeImage("already-there")
    new_img = FakeImage("copied-after")

    monkeypatch.setattr(
        nodes, "read_clipboard_image", _queue_reader([old_img, old_img, new_img])
    )
    monkeypatch.setattr(nodes, "hash_image", lambda img: img.tag)

    node = nodes.ClipboardImageInput()
    tensor, mask = node.wait_for_image(poll_interval=0.01, timeout=0, ignore_current=True)

    assert tensor.tag == "copied-after"


def test_image_node_returns_immediately_when_not_ignoring_current(monkeypatch, fake_pil_conversion):
    existing_img = FakeImage("already-there")

    monkeypatch.setattr(nodes, "read_clipboard_image", _queue_reader([existing_img]))
    monkeypatch.setattr(nodes, "hash_image", lambda img: img.tag)

    node = nodes.ClipboardImageInput()
    tensor, _mask = node.wait_for_image(poll_interval=0.01, timeout=0, ignore_current=False)

    assert tensor.tag == "already-there"


def test_image_node_times_out_when_nothing_new_is_copied(monkeypatch):
    monkeypatch.setattr(nodes, "read_clipboard_image", lambda: None)

    # Fake a clock that advances well past the timeout after a couple calls,
    # so the test doesn't have to actually wait.
    fake_now = [0.0]

    def _time():
        fake_now[0] += 0.6
        return fake_now[0]

    monkeypatch.setattr(nodes.time, "time", _time)

    node = nodes.ClipboardImageInput()
    with pytest.raises(TimeoutError):
        node.wait_for_image(poll_interval=0.01, timeout=1, ignore_current=False)


def test_image_node_respects_cancel_interrupt(monkeypatch, fake_model_management):
    def _raise_interrupt():
        raise KeyboardInterrupt("simulated Cancel from ComfyUI UI")

    monkeypatch.setattr(
        fake_model_management, "throw_exception_if_processing_interrupted", _raise_interrupt
    )
    monkeypatch.setattr(nodes, "read_clipboard_image", lambda: None)

    node = nodes.ClipboardImageInput()
    with pytest.raises(KeyboardInterrupt):
        node.wait_for_image(poll_interval=0.01, timeout=0, ignore_current=False)


# ---------------------------------------------------------------------------
# ClipboardTextInput
# ---------------------------------------------------------------------------

def test_text_node_ignores_preexisting_clipboard_content(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "read_clipboard_text",
        _queue_reader(["already there", "already there", "new text"]),
    )
    monkeypatch.setattr(nodes, "hash_text", lambda text: text)

    node = nodes.ClipboardTextInput()
    (result,) = node.wait_for_text(poll_interval=0.01, timeout=0, ignore_current=True)

    assert result == "new text"


def test_text_node_returns_immediately_when_not_ignoring_current(monkeypatch):
    monkeypatch.setattr(nodes, "read_clipboard_text", _queue_reader(["already there"]))
    monkeypatch.setattr(nodes, "hash_text", lambda text: text)

    node = nodes.ClipboardTextInput()
    (result,) = node.wait_for_text(poll_interval=0.01, timeout=0, ignore_current=False)

    assert result == "already there"


def test_text_node_times_out_when_nothing_new_is_copied(monkeypatch):
    monkeypatch.setattr(nodes, "read_clipboard_text", lambda: None)

    fake_now = [0.0]

    def _time():
        fake_now[0] += 0.6
        return fake_now[0]

    monkeypatch.setattr(nodes.time, "time", _time)

    node = nodes.ClipboardTextInput()
    with pytest.raises(TimeoutError):
        node.wait_for_text(poll_interval=0.01, timeout=1, ignore_current=False)


def test_node_class_and_display_name_mappings_stay_in_sync():
    assert set(nodes.NODE_CLASS_MAPPINGS) == set(nodes.NODE_DISPLAY_NAME_MAPPINGS)
    assert nodes.NODE_CLASS_MAPPINGS["ClipboardImageInput"] is nodes.ClipboardImageInput
    assert nodes.NODE_CLASS_MAPPINGS["ClipboardTextInput"] is nodes.ClipboardTextInput
