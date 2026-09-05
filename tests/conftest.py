"""
Shared test fixtures.

nodes.py does `import comfy.model_management as model_management`, but the
`comfy` package only exists inside a running ComfyUI installation. To unit
test the nodes without installing all of ComfyUI, we register a lightweight
fake `comfy.model_management` module before anything imports nodes.py.
"""
import pathlib
import sys
import types

import pytest
--ignore __init__.py
# nodes.py lives at the repo root and does `from .clipboard_backend import
# ...` (relative import), which only works if it's loaded as part of a
# package. ComfyUI achieves this by importing the whole custom_nodes folder
# as a package at runtime. For tests we register a lightweight package
# pointing at the repo root so `from comfyui_clipboard_nodes import nodes`
# resolves the relative import correctly.
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGE_NAME = "comfyui_clipboard_nodes"


def _install_package_for_relative_imports():
    if PACKAGE_NAME in sys.modules:
        return
    pkg = types.ModuleType(PACKAGE_NAME)
    pkg.__path__ = [str(REPO_ROOT)]
    sys.modules[PACKAGE_NAME] = pkg


_install_package_for_relative_imports()


def _install_fake_comfy():
    if "comfy" in sys.modules and "comfy.model_management" in sys.modules:
        return

    comfy_pkg = types.ModuleType("comfy")
    model_management = types.ModuleType("comfy.model_management")

    def throw_exception_if_processing_interrupted():
        # Real ComfyUI raises comfy.model_management.InterruptProcessingException
        # here if the user hit Cancel. Tests that want to simulate a Cancel
        # mid-wait should monkeypatch this function to actually raise.
        return None

    model_management.throw_exception_if_processing_interrupted = (
        throw_exception_if_processing_interrupted
    )
    comfy_pkg.model_management = model_management

    sys.modules["comfy"] = comfy_pkg
    sys.modules["comfy.model_management"] = model_management


def _install_fake_torch():
    """
    nodes.py imports torch at module level purely to build an output tensor
    in `_pil_to_tensor`. Pulling in real PyTorch just to unit-test the
    clipboard polling logic is unnecessary weight for CI, so we stub it out
    if it isn't already installed. If a real torch is present (e.g. running
    tests inside an actual ComfyUI environment), we leave it alone.
    """
    try:
        import torch  # noqa: F401
        return
    except ImportError:
        pass

    torch_stub = types.ModuleType("torch")
    torch_stub.from_numpy = lambda arr: arr
    torch_stub.zeros = lambda *args, **kwargs: None
    sys.modules["torch"] = torch_stub


_install_fake_comfy()
_install_fake_torch()


@pytest.fixture
def fake_model_management():
    """Returns the stubbed comfy.model_management module for monkeypatching."""
    return sys.modules["comfy.model_management"]
