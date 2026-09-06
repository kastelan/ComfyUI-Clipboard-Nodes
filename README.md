# Clipboard-Automator

In-graph replacement for [ComfyUI-Clipboard-Workflow-Automator](https://github.com/kastelan/ComfyUI-Clipboard-Workflow-Automator).
Instead of a separate script polling the clipboard and pushing prompts to the
API, these are **nodes that live inside the workflow itself**: when executed,
they block/poll until new clipboard content appears, then output it.

## Nodes

- **Clipboard Image Input (wait)** → `IMAGE`, `MASK`
- **Clipboard Text Input (wait)** → `STRING`

Both take:

| Input            | Meaning                                                                 |
| ---------------- | ------------------------------------------------------------------------ |
| `poll_interval`  | Seconds between clipboard checks (default 0.5)                          |
| `timeout`        | Give up after N seconds with nothing new; `0` = wait forever            |
| `ignore_current` | On the node's first run, ignore whatever's already on the clipboard (mirrors the old script's "startup skip") |

## Install
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/kastelan/Clipboard-Automator.git

cd Clipboard-Automator
pip install -r requirements.txt   # or: pip install .
```

**Linux** additionally needs system GTK bindings for `PyGObject`:

```
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

Restart ComfyUI. The nodes appear under the **clipboard** category.

## Usage

1. Add **Clipboard Image Input** or **Clipboard Text Input** where you'd
   normally put `LoadImage` / `CLIPTextEncode`'s text widget.
2. Queue the prompt. Execution pauses on that node until you copy something.
3. To get continuous monitoring like the old script: enable **Auto Queue**
   (dropdown next to the Queue button in the ComfyUI UI). The graph
   re-runs automatically after each completion, and the clipboard node
   waits for the *next* change each time.
4. Cancel/Interrupt in the UI works normally — it breaks out of the wait
   loop cleanly (via `comfy.model_management.throw_exception_if_processing_interrupted`).

## Why this instead of the standalone script

| | Script (`clipboard.py`) | These nodes |
|---|---|---|
| Runs as | separate process | part of the ComfyUI graph |
| Multiple workflows | via `--profile` files | just build different graphs |
| Retry/dead-letter queue | yes (own HTTP calls) | not needed — ComfyUI owns execution |
| Setup | `config.toml`, node titles (`load_clipboard_image`) | drag a node in, no config file |
| Stopping mid-wait | Ctrl+C in terminal | Cancel button in ComfyUI UI |

Trade-off: while a clipboard node is waiting, that slot in the queue is
occupied (same as any other long-running node) — you can't run other
prompts concurrently on the same ComfyUI instance in the meantime.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
