#!/usr/bin/env python3
"""Ptyxis Workspace Launcher.

IMPORTANT! AFTER ANY CHANGES RUN:
update-desktop-database ~/.local/share/applications

Automates the opening of multiple terminal tabs with custom titles and working
directories based on machine-specific configuration packages.

Features:
    - Loads configuration dynamically from a local `config` package based on
      system hostname.
    - Resolves tab working directories relative to $HOME using pathlib.
    - Validates that target directories exist before launching, sending a native
      desktop notification (via notify-send on Linux or osascript on macOS)
      if a path is missing.
    - Communicates cleanly with the Ptyxis terminal daemon using staggered
      subprocess spawning.

"""

"""
AFTER ANY CHANGES, RUN ==>
update-desktop-database ~/.local/share/applications
"""

import importlib
from pathlib import Path
import socket
import subprocess
import sys
import time

SCRIPT_DIR = Path(__file__).resolve().parent
# Ensure parent directory is in sys.path so Python can find the 'config' package
sys.path.insert(0, str(SCRIPT_DIR))

HOSTNAME = socket.gethostname().lower()


def notify(title, message):
    """Triggers a native desktop notification cross-platform (Linux / macOS)."""
    try:
        if sys.platform == "darwin":  # macOS
            # Escape quotes for AppleScript
            safe_title = title.replace('"', '\\"')
            safe_msg = message.replace('"', '\\"')
            script = f'display notification "{safe_msg}" with title "{safe_title}"'
            subprocess.run(["osascript", "-e", script])
        else:  # Default to Linux / notify-send
            subprocess.run(["notify-send", title, message])
    except Exception:
        # Fallback if notification tool fails or isn't present
        pass


def load_tabs() -> list | None:
    # Try loading machine-specific config (e.g., config.fw16), fall back to config.default
    module_name = f"config.{HOSTNAME}"
    try:
        mod = importlib.import_module(module_name)
        return getattr(mod, "config", [])
    except ModuleNotFoundError as ex:
        notify(f"Cound not load {module_name}: {ex}")
        try:
            mod = importlib.import_module("config.default")
            return getattr(mod, "config", [])
        except Exception as e:
            notify(
                "Terminal Launcher Error",
                f"Could not load default config for '{HOSTNAME}': {e}",
            )
            return None
    except Exception as e:
        notify(
            "Terminal Launcher Error", f"Syntax or load error in {module_name}: {e}"
        )
        return None


def main():
    tabs = load_tabs()
    if tabs is None:
        return
    elif not tabs:
        notify(f"No tabs found in config file {HOSTNAME}.py")
        return

    home = Path.home()
    valid_tabs = []

    # Validate paths using pathlib
    for tab in tabs:
        full_path = home / tab.path
        if full_path.is_dir():
            valid_tabs.append((tab.title, full_path))
        else:
            notify(
                "Terminal Launcher Warning",
                f"Skipping tab '{tab.title}': Directory not found\n{full_path}",
            )

    if not valid_tabs:
        notify("Terminal Launcher Error", "No valid tab paths found to open!")
        return

    # Open the first valid tab in a brand new window
    title, path = valid_tabs[0]
    subprocess.Popen(["ptyxis", "--new-window", "-T", title, "-d", str(path)])
    time.sleep(0.2)  # Breathing room for the Ptyxis daemon

    # Open the remaining valid tabs
    for title, path in valid_tabs[1:]:
        subprocess.Popen(["ptyxis", "--tab", "-T", title, "-d", str(path)])
        time.sleep(0.1)

    notify(f"Loaded {len(tabs)} tabs")


if __name__ == "__main__":
    main()
