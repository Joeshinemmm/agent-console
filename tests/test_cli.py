import subprocess
import sys

import pytest
from conftest import FIXTURES


def invoke(*arguments, input=None):
    return subprocess.run(
        [sys.executable, "-m", "agent_console", *arguments],
        input=input,
        capture_output=True,
        timeout=15,
    )


def test_help():
    result = invoke("--help")
    assert result.returncode == 0
    assert b"replay" in result.stdout and b"run" in result.stdout


@pytest.mark.parametrize(
    "filename,status,exit_code",
    [
        ("successful_developer_run.jsonl", b"COMPLETED", 0),
        ("failed_run.jsonl", b"FAILED", 1),
        ("legacy_codex_run.jsonl", b"COMPLETED", 0),
    ],
)
def test_plain_cli(filename, status, exit_code):
    result = invoke("replay", str(FIXTURES / filename), "--plain")
    assert result.returncode == exit_code
    assert status in result.stdout
    assert b"Traceback" not in result.stderr


def test_plain_cli_shows_provider_without_session_identifiers():
    result = invoke("replay", str(FIXTURES / "successful_developer_run.jsonl"), "--plain")
    assert result.returncode == 0
    assert b"LLM turn completed (Claude)" in result.stdout
    assert b"llm=Completed" in result.stdout
    assert b"LLM provider: claude" in result.stdout
    assert b"synthetic-thread-id" not in result.stdout + result.stderr
    assert b"claude_login" not in result.stdout + result.stderr


def test_plain_cli_reads_legacy_codex_records():
    result = invoke("replay", str(FIXTURES / "legacy_codex_run.jsonl"), "--plain")
    assert result.returncode == 0
    assert b"Codex turn completed" in result.stdout
    assert b"llm=Completed" in result.stdout
    assert b"codex=" not in result.stdout
    assert b"LLM provider: codex" in result.stdout


def test_cli_stdin(encode_event):
    result = invoke("replay", "-", input=encode_event(1, "run.completed"))
    assert result.returncode == 0
    assert b"COMPLETED" in result.stdout


def test_cli_subprocess():
    result = invoke(
        "run",
        "--plain",
        "--",
        sys.executable,
        "-u",
        "-c",
        "import pathlib,sys; sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())",
        str(FIXTURES / "successful_developer_run.jsonl"),
    )
    assert result.returncode == 0
    assert b"Process exit 0" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("run", "--"),
        ("replay", "-", "--tui"),
        ("replay", "missing-file.jsonl"),
        ("replay", "unused", "--delay", "nan"),
        ("replay", "unused", "--delay", "-1"),
    ],
)
def test_cli_friendly_errors(args):
    result = invoke(*args)
    assert result.returncode == 2
    assert b"Traceback" not in result.stderr + result.stdout


def test_cli_no_freeform_or_metadata_leak(encode_event):
    raw = encode_event(
        1,
        "run.completed",
        message="synthetic-prompt-body",
        metadata={"Authorization": "synthetic-secret"},
    )
    result = invoke("replay", "-", input=raw)
    assert result.returncode == 0
    assert b"synthetic-prompt-body" not in result.stdout + result.stderr
    assert b"synthetic-secret" not in result.stdout + result.stderr
