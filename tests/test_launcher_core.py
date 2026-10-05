import asyncio
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from agent_console.cli import main
from agent_console.launcher.command import LaunchRequest, build_command, preflight
from agent_console.launcher.controller import LaunchController, workspace_result
from agent_console.launcher.profile import (
    PROFILE_FIELDS,
    LaunchError,
    ProfileBook,
    RuntimeProfile,
    config_path,
    load_profiles,
    save_profiles,
)
from agent_console.sources import SourceItem
from agent_console.state.session import Session, consume

FAKE = Path(__file__).with_name("fake_launcher_runtime.py")


@pytest.fixture
def runtime():
    return RuntimeProfile("synthetic.local", sys.executable, str(FAKE), "synthetic-model")


@pytest.fixture
def request_data(tmp_path):
    workspace = tmp_path / "workspace with spaces"
    workspace.mkdir()
    return LaunchRequest(
        str(workspace), 'synthetic "quote" & | ; $(ignored) --flag', model="override-model"
    )


def test_profile_roundtrip_missing_and_selection(tmp_path, runtime):
    path = tmp_path / "agent-console.local.toml"
    assert not load_profiles(path).profiles
    with pytest.raises(LaunchError):
        load_profiles(path).select()
    book = ProfileBook({runtime.name: runtime}, runtime.name)
    save_profiles(path, book)
    assert load_profiles(path) == book
    assert book.select() == runtime
    assert book.select(runtime.name) == runtime
    assert set(PROFILE_FIELDS) == {
        "python_executable",
        "ai_agent_main",
        "model",
        "provider",
        "default_verify",
        "default_max_retries",
    }


def test_profile_unicode_path_roundtrip(tmp_path, runtime):
    entry = tmp_path / "runtime-한글-\U0001f680.py"
    entry.write_text("# synthetic", encoding="utf-8")
    profile = replace(runtime, ai_agent_main=str(entry))
    book = ProfileBook({profile.name: profile}, profile.name)
    path = tmp_path / "agent-console.local.toml"
    save_profiles(path, book)
    assert load_profiles(path) == book


def test_invalid_save_preserves_existing_config(tmp_path, runtime):
    path = tmp_path / "agent-console.local.toml"
    book = ProfileBook({runtime.name: runtime}, runtime.name)
    save_profiles(path, book)
    original = path.read_bytes()
    book.profiles[runtime.name] = replace(runtime, model="--invalid")
    with pytest.raises(LaunchError):
        save_profiles(path, book)
    assert path.read_bytes() == original


def test_noninteractive_launch(tmp_path, capsys):
    assert main(["launch", "--config", str(tmp_path / "agent-console.local.toml")]) == 2
    assert "interactive terminal" in capsys.readouterr().err


@pytest.mark.parametrize(
    "contents",
    [
        "broken = [",
        "config_version = 2",
        "x" * 65537,
        'config_version = 1\npassword = "synthetic"',
        'config_version = 1\n[profiles.local]\ntoken = "synthetic"',
    ],
    ids=["syntax", "version", "oversize", "root-secret", "profile-secret"],
)
def test_invalid_config_safe_errors(tmp_path, contents):
    path = tmp_path / "agent-console.local.toml"
    path.write_text(contents)
    with pytest.raises(LaunchError, match="Invalid runtime config"):
        load_profiles(path)


@pytest.mark.parametrize("field", ["python_executable", "ai_agent_main"])
def test_missing_runtime_files(tmp_path, runtime, field):
    profile = replace(runtime, **{field: str(tmp_path / "missing.py")})
    with pytest.raises(LaunchError):
        profile.validate_files()


def test_config_path_override_and_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config_path() == tmp_path / "agent-console" / "config.toml"
    assert config_path(str(tmp_path / "agent-console.local.toml")).parent == tmp_path
    with pytest.raises(LaunchError):
        config_path(str(tmp_path / "tracked.toml"))


def test_profile_cli_lifecycle(tmp_path, runtime, capsys):
    base = ["profile", "--config", str(tmp_path / "agent-console.local.toml")]
    assert main(base + ["list"]) == 0
    assert "No runtime" in capsys.readouterr().out
    assert (
        main(
            base
            + [
                "add",
                runtime.name,
                "--python",
                runtime.python_executable,
                "--main",
                runtime.ai_agent_main,
                "--model",
                runtime.model,
            ]
        )
        == 0
    )
    assert main(base + ["select", runtime.name]) == 0
    assert main(base + ["show", runtime.name]) == 0
    assert runtime.model in capsys.readouterr().out
    assert main(base + ["remove", runtime.name]) == 0
    assert not load_profiles(Path(base[2])).profiles


@pytest.mark.parametrize("verify", ["none", "pytest", "web"])
@pytest.mark.parametrize("allow", [False, True])
def test_command_exact_argv(runtime, request_data, verify, allow):
    request = replace(request_data, verify=verify, allow_execution=allow, max_retries=3)
    argv = build_command(runtime, request)
    assert argv == [
        sys.executable,
        "-u",
        str(FAKE),
        "--workspace",
        request.workspace,
        "--task",
        "developer",
        "--provider",
        "codex",
        "--codex-model",
        "override-model",
        "--max-retries",
        "3",
        "--verify",
        verify,
        "--output",
        "jsonl",
    ] + (["--allow-execution"] if allow else []) + ["--", request.prompt]
    assert request.prompt not in repr(request)


def test_check_omits_all_execution_options(runtime, request_data):
    request = replace(request_data, allow_execution=True, prompt="", verify="invalid")
    assert build_command(runtime, request, check=True) == [
        sys.executable,
        "-u",
        str(FAKE),
        "--workspace",
        request.workspace,
        "--check-workspace",
        "--output",
        "jsonl",
    ]


@pytest.mark.parametrize(
    "changes",
    [
        {"workspace": ""},
        {"workspace": "relative"},
        {"prompt": " "},
        {"prompt": "x\0"},
        {"verify": "unknown"},
        {"max_retries": -1},
        {"max_retries": 4},
        {"max_retries": True},
        {"provider": "unknown"},
        {"task": "desktop"},
        {"model": "--bad"},
        {"allow_execution": 1},
    ],
)
def test_invalid_request(runtime, request_data, changes):
    with pytest.raises(LaunchError):
        preflight(runtime, replace(request_data, **changes))


def test_nonexistent_workspace(runtime, request_data):
    with pytest.raises(LaunchError, match="does not exist"):
        preflight(runtime, replace(request_data, workspace=request_data.workspace + "missing"))


async def test_controller_single_process_and_fake_success(runtime, request_data):
    controller = LaunchController()
    source = controller.begin(runtime, replace(request_data, allow_execution=True))
    with pytest.raises(LaunchError, match="already active"):
        controller.begin(runtime, request_data)
    await consume(source, controller.session)
    assert not controller.active
    assert controller.session.exit_code == 0
    assert (Path(request_data.workspace) / "docs/example.md").is_file()
    assert request_data.prompt not in repr(controller.session)


@pytest.mark.parametrize("denied", [False, True])
async def test_workspace_check_fake(runtime, tmp_path, denied):
    workspace = tmp_path / ("denied" if denied else "valid")
    workspace.mkdir()
    controller = LaunchController()
    await consume(
        controller.begin(runtime, LaunchRequest(str(workspace)), check=True), controller.session
    )
    assert not list(workspace.iterdir())
    assert ("failed" if denied else "Valid") in workspace_result(controller.session)


@pytest.mark.parametrize("case", ["missing", "error", "invalid", "nonzero", "cancelled"])
def test_workspace_check_requires_complete_success(encode_event, case):
    session = Session()
    session.accept(SourceItem("line", encode_event(1, "run.started")))
    if case != "missing":
        session.accept(
            SourceItem(
                "line",
                encode_event(
                    2,
                    "workspace.validated",
                    status="completed",
                    level="error" if case == "error" else "info",
                ),
            )
        )
    session.accept(SourceItem("line", encode_event(2 if case == "missing" else 3, "run.completed")))
    if case == "invalid":
        session.accept(SourceItem("line", b"not-json"))
    session.accept(SourceItem("exit", 1 if case == "nonzero" else 0))
    session.cancelled = case == "cancelled"
    session.finish()
    assert "failed" in workspace_result(session)


async def test_controller_cancel(runtime, request_data):
    controller = LaunchController()
    source = controller.begin(runtime, replace(request_data, prompt="synthetic-wait"))
    task = asyncio.create_task(consume(source, controller.session))
    for _ in range(100):
        if controller.session.runs:
            break
        await asyncio.sleep(0.02)
    assert controller.session.runs
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not controller.active
    assert controller.session.cancelled
    assert controller.session.process_exit is not None
    assert controller.session.exit_code == 130


async def test_controller_close_before_first_read(runtime, request_data):
    controller = LaunchController()
    source = controller.begin(runtime, request_data)
    await source.aclose()
    assert not controller.active
    next_source = controller.begin(runtime, request_data)
    await source.aclose()
    assert controller.active
    await next_source.aclose()
    assert not controller.active


@pytest.mark.parametrize(
    "path",
    [
        "/absolute/file",
        "../file",
        "docs/../file",
        "C:/file",
        "docs/.env",
        "auth.json",
        "docs/a\x1b.md",
        "docs/token.txt",
    ],
)
def test_file_metadata_rejects_unsafe_path(make_event, path):
    assert make_event(event_type="file.created", metadata={"path": path}).details.path is None


def test_metadata_projection(make_event):
    event = make_event(
        event_type="file.created",
        metadata={
            "path": "docs/example.md",
            "source": "synthetic-hidden",
            "prompt": "synthetic-hidden",
        },
    )
    assert event.details.path == "docs/example.md"
    assert "synthetic-hidden" not in repr(event)
    assert (
        make_event(
            event_type="git.status", metadata={"git_repository": "true"}
        ).details.git_repository
        is None
    )


def test_source_boundary_and_no_personal_hardcoding():
    root = Path(__file__).parents[1] / "src"
    for path in root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for forbidden in (
            "C:" + "\\Users\\",
            "gpt-" + "6-sol",
            "shell=" + "True",
            "import " + "ai_agent",
            "from " + "ai_agent",
            "import " + "openai",
        ):
            assert forbidden not in source, path.name
