"""Interchangeable async streams: files, stdin, and external processes."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class SourceItem:
    kind: Literal["line", "issue", "stderr", "exit"]
    value: bytes | str | int
