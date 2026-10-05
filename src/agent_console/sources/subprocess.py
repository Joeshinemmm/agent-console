import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import suppress

from agent_console.protocol.jsonl import LineFramer
from agent_console.sources import SourceItem


async def subprocess_source(
    command: Sequence[str], *, on_exit: Callable[[int | None], None] | None = None
) -> AsyncGenerator[SourceItem, None]:
    """Execute argv directly. Drain both pipes concurrently; never expose stderr text."""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except (OSError, ValueError):
        yield SourceItem("issue", "Cannot start command; check executable and arguments.")
        yield SourceItem("exit", 127)
        return
    items: asyncio.Queue[SourceItem | None] = asyncio.Queue(maxsize=128)

    async def read_stdout() -> None:
        assert process.stdout is not None
        framer = LineFramer()

        async def emit(lines: list[bytes | None]) -> None:
            for line in lines:
                if line is None:
                    await items.put(SourceItem("issue", "JSONL line exceeds 64 KiB; discarded."))
                else:
                    await items.put(SourceItem("line", line))

        try:
            while chunk := await process.stdout.read(8192):
                await emit(framer.feed(chunk))
            await emit(framer.finish())
        except OSError:
            await items.put(SourceItem("issue", "Cannot read subprocess stdout."))
        await items.put(None)

    async def read_stderr() -> None:
        assert process.stderr is not None
        try:
            while chunk := await process.stderr.read(8192):
                await items.put(SourceItem("stderr", len(chunk)))
        except OSError:
            await items.put(SourceItem("issue", "Cannot read subprocess stderr."))
        await items.put(None)

    readers = [asyncio.create_task(read_stdout()), asyncio.create_task(read_stderr())]
    try:
        finished = 0
        while finished < 2:
            item = await items.get()
            if item is None:
                finished += 1
            else:
                yield item
        yield SourceItem("exit", await process.wait())
    finally:
        if process.returncode is None:
            with suppress(ProcessLookupError):
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                with suppress(ProcessLookupError):
                    process.kill()
                # Pipe-owning descendants must not keep shutdown waiting forever.
                with suppress(TimeoutError):
                    await asyncio.wait_for(process.wait(), timeout=2)
        for reader in readers:
            reader.cancel()
        await asyncio.gather(*readers, return_exceptions=True)
        if on_exit is not None:
            on_exit(process.returncode)
