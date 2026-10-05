from dataclasses import dataclass, field
from pathlib import Path

from agent_console.launcher.profile import (
    VERIFY_MODES,
    LaunchError,
    RuntimeProfile,
    identifier,
    retries,
)


@dataclass(frozen=True)
class LaunchRequest:
    workspace: str = field(repr=False)
    prompt: str = field(default="", repr=False)
    task: str = "developer"
    provider: str = "codex"
    model: str = ""
    verify: str = "none"
    max_retries: int = 0
    allow_execution: bool = False

    def validate(self, *, check: bool = False) -> None:
        if (
            not isinstance(self.workspace, str)
            or not self.workspace.strip()
            or len(self.workspace) > 4096
            or any(ord(char) < 32 for char in self.workspace)
            or not Path(self.workspace).is_absolute()
        ):
            raise LaunchError("Workspace must be a non-empty absolute directory path.")
        if check:
            return
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise LaunchError("Enter a prompt before starting a run.")
        if "\x00" in self.prompt or len(self.prompt) > 12000:
            raise LaunchError("Prompt must contain at most 12,000 characters and no NUL.")
        if self.task != "developer" or self.provider != "codex":
            raise LaunchError("This launcher supports the Developer task with Codex.")
        identifier(self.model, "model")
        if self.verify not in VERIFY_MODES:
            raise LaunchError("Verify must be none, pytest, or web.")
        retries(self.max_retries)
        if type(self.allow_execution) is not bool:
            raise LaunchError("Allow execution must be an explicit checkbox value.")


def build_command(
    profile: RuntimeProfile, request: LaunchRequest, *, check: bool = False
) -> list[str]:
    """Pure argv construction; the prompt is one positional argument after --."""
    profile.validate()
    request.validate(check=check)
    argv = [
        profile.python_executable,
        "-u",
        profile.ai_agent_main,
        "--workspace",
        request.workspace,
    ]
    if check:
        return argv + ["--check-workspace", "--output", "jsonl"]
    argv += [
        "--task",
        request.task,
        "--provider",
        request.provider,
        "--codex-model",
        request.model,
        "--max-retries",
        str(request.max_retries),
        "--verify",
        request.verify,
        "--output",
        "jsonl",
    ]
    if request.allow_execution:
        argv.append("--allow-execution")
    return argv + ["--", request.prompt]


def preflight(profile: RuntimeProfile, request: LaunchRequest, *, check: bool = False) -> None:
    profile.validate_files()
    request.validate(check=check)
    try:
        if not Path(request.workspace).is_dir():
            raise LaunchError("Workspace directory does not exist.")
    except OSError:
        raise LaunchError("Cannot inspect the workspace directory.") from None
