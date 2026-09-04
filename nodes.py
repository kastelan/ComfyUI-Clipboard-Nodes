"""
Custom ComfyUI nodes that block/poll on the OS clipboard when executed,
replacing the external clipboard.py monitor script with an in-graph node.

Combine with ComfyUI's built-in "Auto Queue" (Extra options, in the queue
button dropdown) to get continuous monitoring: the graph re-runs on every
completion, and these nodes each wait for the next clipboard change.
"""

import time

import numpy as np
import torch

import comfy.model_management as model_management

from .clipboard_backend import (
    read_clipboard_image,
    read_clipboard_text,
    hash_image,
    hash_text,
)

CATEGORY = "clipboard"


def _pil_to_tensor(img):
    img = img.convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None,]
    mask = torch.zeros((1, img.size[1], img.size[0]), dtype=torch.float32)
    return tensor, mask


class ClipboardImageInput:
    """Waits until a new image appears on the clipboard, then outputs it."""

    def __init__(self):
        self._last_hash = None
        self._initialized = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "poll_interval": ("FLOAT", {
                    "default": 0.5, "min": 0.05, "max": 5.0, "step": 0.05,
                    "tooltip": "Seconds between clipboard checks.",
                }),
                "timeout": ("INT", {
                    "default": 0, "min": 0, "max": 3600, "step": 1,
                    "tooltip": "Give up after N seconds with no new image. 0 = wait forever.",
                }),
                "ignore_current": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "On this node's first run, ignore whatever is already on "
                               "the clipboard and wait for the next change.",
                }),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("image", "mask")
    FUNCTION = "wait_for_image"
    CATEGORY = CATEGORY
    DESCRIPTION = "Blocks until a new image is copied to the clipboard, then outputs it."

    def wait_for_image(self, poll_interval, timeout, ignore_current):
        if not self._initialized:
            if ignore_current:
                current = read_clipboard_image()
                if current is not None:
                    self._last_hash = hash_image(current)
            self._initialized = True

        start = time.time()
        while True:
            model_management.throw_exception_if_processing_interrupted()

            img = read_clipboard_image()
            if img is not None:
                h = hash_image(img)
                if h != self._last_hash:
                    self._last_hash = h
                    tensor, mask = _pil_to_tensor(img)
                    return (tensor, mask)

            if timeout and (time.time() - start) > timeout:
                raise TimeoutError(f"No new clipboard image within {timeout}s")

            time.sleep(poll_interval)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always report "changed" so this node re-executes on every queue run
        # (needed for Auto Queue to re-trigger the wait instead of reusing
        # the cached output).
        return float("nan")


class ClipboardTextInput:
    """Waits until new text appears on the clipboard, then outputs it."""

    def __init__(self):
        self._last_hash = None
        self._initialized = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "poll_interval": ("FLOAT", {
                    "default": 0.5, "min": 0.05, "max": 5.0, "step": 0.05,
                    "tooltip": "Seconds between clipboard checks.",
                }),
                "timeout": ("INT", {
                    "default": 0, "min": 0, "max": 3600, "step": 1,
                    "tooltip": "Give up after N seconds with no new text. 0 = wait forever.",
                }),
                "ignore_current": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "On this node's first run, ignore whatever is already on "
                               "the clipboard and wait for the next change.",
                }),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "wait_for_text"
    CATEGORY = CATEGORY
    DESCRIPTION = "Blocks until new text is copied to the clipboard, then outputs it."

    def wait_for_text(self, poll_interval, timeout, ignore_current):
        if not self._initialized:
            if ignore_current:
                current = read_clipboard_text()
                if current is not None:
                    self._last_hash = hash_text(current)
            self._initialized = True

        start = time.time()
        while True:
            model_management.throw_exception_if_processing_interrupted()

            text = read_clipboard_text()
            if text is not None:
                h = hash_text(text)
                if h != self._last_hash:
                    self._last_hash = h
                    return (text,)

            if timeout and (time.time() - start) > timeout:
                raise TimeoutError(f"No new clipboard text within {timeout}s")

            time.sleep(poll_interval)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")


NODE_CLASS_MAPPINGS = {
    "ClipboardImageInput": ClipboardImageInput,
    "ClipboardTextInput": ClipboardTextInput,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ClipboardImageInput": "Clipboard Image Input (wait)",
    "ClipboardTextInput": "Clipboard Text Input (wait)",
}
