import asyncio
import queue
import threading
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import BinaryIO

from agent_console.protocol.jsonl import MAX_LINE_BYTES
from agent_console.sources import SourceItem


def read_line(stream: BinaryIO) -> SourceItem | None:
    line = stream.readline(MAX_LINE_BYTES + 2)
    if not line:
        return None
    if len(line.removesuffix(b"\n")) > MAX_LINE_BYTES:
        while line and not line.endswith(b"\n"):
            line = stream.readline(MAX_LINE_BYTES + 1)
        return SourceItem("issue", "JSONL line exceeds 64 KiB; discarded.")
    return SourceItem("line", line)


async def file_source(path: Path, delay: float = 0) -> AsyncGenerator[SourceItem, None]:
    try:
        with path.open("rb") as stream:
            while (item := read_line(stream)) is not None:
                yield item
                await asyncio.sleep(delay)
    except OSError:
        yield SourceItem("issue", "Cannot read event file; check the path and permissions.")


async def stdin_source(stream: BinaryIO) -> AsyncGenerator[SourceItem, None]:
    # A daemon reader avoids blocking the UI or asyncio shutdown on an open pipe.
    items: queue.Queue[SourceItem | None] = queue.Queue(maxsize=128)
    stopped = threading.Event()

    def send(item: SourceItem | None) -> bool:
        while not stopped.is_set():
            try:
                items.put(item, timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def read() -> None:
        try:
            while not stopped.is_set():
                item = read_line(stream)
                if not send(item) or item is None:
                    return
        except OSError:
            send(SourceItem("issue", "Cannot read stdin stream."))
            send(None)

    threading.Thread(target=read, daemon=True, name="jsonl-stdin").start()
    try:
        while True:
            try:
                item = items.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.02)
                continue
            if item is None:
                break
            yield item
            await asyncio.sleep(0)
    finally:
        stopped.set()
