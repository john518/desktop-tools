"""Data schema for terminal configurations."""

from dataclasses import dataclass

@dataclass
class TerminalTab:
    title: str
    path: str  # relative to $HOME
