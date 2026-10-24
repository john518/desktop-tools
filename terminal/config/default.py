"""Default configuration USED if <hostname>.py not found.

Layout is a list of TerminalTab(label, path) instances.
Note that <path> is relative to $HOME.
"""

from .schema import TerminalTab

config = [
    TerminalTab("home", ""),
    TerminalTab("projects", "projects"),
]
