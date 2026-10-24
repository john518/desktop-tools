""""""

from dataclasses import dataclass

@dataclass
class TerminalTab:
    title: str
    path: str  # relative to $HOME
