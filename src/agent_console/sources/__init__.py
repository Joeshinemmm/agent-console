"""Interchangeable async streams: files, stdin, and external processes."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class SourceItem:
    kind: Literal["line", "issue", "stderr", "exit"]
    value: bytes | str | int


class ClosableSource(Protocol):
    def __aiter__(self) -> AsyncIterator[SourceItem]: ...

    async def aclose(self) -> None: ...
