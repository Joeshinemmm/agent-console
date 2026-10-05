from collections.abc import AsyncGenerator, Callable
from contextlib import aclosing

from agent_console.launcher.command import LaunchRequest, build_command, preflight
from agent_console.launcher.profile import LaunchError, RuntimeProfile
from agent_console.models.run import Status
from agent_console.sources import SourceItem
from agent_console.sources.subprocess import subprocess_source
from agent_console.state.session import Session


class LaunchStream:
    """Release a launch reservation even when cancelled before the first read."""

    def __init__(self, source: AsyncGenerator[SourceItem, None], release: Callable[[], None]):
        self.source = source
        self.release = release
        self.closed = False

    def __aiter__(self) -> "LaunchStream":
        return self

    async def __anext__(self) -> SourceItem:
        if self.closed:
            raise StopAsyncIteration
        try:
            return await anext(self.source)
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        if not self.closed:
            self.closed = True
            try:
                await self.source.aclose()
            finally:
                self.release()


class LaunchController:
    """One directly owned process per launcher, including workspace checks."""

    def __init__(self) -> None:
        self.active = False
        self.session = Session()

    def begin(
        self, profile: RuntimeProfile, request: LaunchRequest, *, check: bool = False
    ) -> LaunchStream:
        if self.active:
            raise LaunchError("A process is already active; wait for it to end.")
        preflight(profile, request, check=check)
        argv = build_command(profile, request, check=check)
        self.session = Session()
        self.active = True

        def release() -> None:
            argv.clear()
            self.active = False

        return LaunchStream(self._stream(argv), release)

    async def _stream(self, argv: list[str]) -> AsyncGenerator[SourceItem, None]:
        session = self.session

        def exited(code: int | None) -> None:
            session.process_exit = code
            session.revision += 1

        async with aclosing(subprocess_source(argv, on_exit=exited)) as source:
            async for item in source:
                yield item


def workspace_result(session: Session) -> str:
    if not session.ended:
        return "Checking workspace…"
    valid = (
        not session.cancelled
        and session.process_exit == 0
        and session.exit_code == 0
        and len(session.runs) == 1
    )
    run = next(iter(session.runs.values()), None)
    evidence = (
        [e for e in run.events if e.event_type == "workspace.validated" and e.status == "completed"]
        if run
        else []
    )
    valid = valid and bool(evidence) and run.status == Status.COMPLETED and run.error_count == 0
    if not valid:
        return (
            f"Workspace check failed or incomplete · Process exit {session.process_exit} · "
            f"Issues {session.issue_count}. Inspect the check monitor; no run was started."
        )
    git_events = [e for e in run.events if e.event_type == "git.status"]
    detail = git_events[-1].details if git_events else None
    repository = {True: "Yes", False: "No", None: "Not reported"}
    git = repository[detail.git_repository if detail else None]
    dirty = repository[detail.git_dirty if detail else None]
    return (
        f"Valid · COMPLETED · Process exit 0 · Git repository: {git} · Dirty: {dirty}\n"
        "Branch/read/write/commit/push permissions: not reported by this JSONL contract.\n"
        "Check success is not execution approval; ai-agent validates again at Start Run."
    )
