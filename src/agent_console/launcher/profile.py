import json
import os
import re
import tempfile
import tomllib
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path

VERIFY_MODES = ("none", "pytest", "web")


class LaunchError(ValueError):
    """User-facing error without input payloads or raw exception details."""


def identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise LaunchError(f"Invalid {label}; use a bounded identifier.")
    return value


def retries(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 3:
        raise LaunchError("Max retries must be an integer from 0 to 3.")
    return value


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    python_executable: str = field(repr=False)
    ai_agent_main: str = field(repr=False)
    model: str
    provider: str = "codex"
    default_verify: str = "none"
    default_max_retries: int = 0

    def validate(self) -> None:
        identifier(self.name, "profile name")
        identifier(self.model, "model")
        if self.provider != "codex":
            raise LaunchError("The external Developer launcher currently supports Codex only.")
        if self.default_verify not in VERIFY_MODES:
            raise LaunchError("Verify must be none, pytest, or web.")
        retries(self.default_max_retries)
        for path in (self.python_executable, self.ai_agent_main):
            if (
                not isinstance(path, str)
                or not path.strip()
                or len(path) > 4096
                or any(ord(char) < 32 for char in path)
                or not Path(path).is_absolute()
            ):
                raise LaunchError("Runtime paths must be non-empty absolute file paths.")
        if Path(self.python_executable).suffix.lower() in (".bat", ".cmd", ".ps1", ".sh"):
            raise LaunchError("Use a Python executable, not a shell script.")
        if Path(self.ai_agent_main).suffix.lower() != ".py":
            raise LaunchError("The runtime entry point must be a Python file.")

    def validate_files(self) -> None:
        self.validate()
        try:
            if not Path(self.python_executable).is_file():
                raise LaunchError("Python executable does not exist or is not a file.")
            if not Path(self.ai_agent_main).is_file():
                raise LaunchError("Runtime main.py does not exist or is not a file.")
        except OSError:
            raise LaunchError("Cannot inspect runtime files.") from None


@dataclass
class ProfileBook:
    profiles: dict[str, RuntimeProfile] = field(default_factory=dict)
    default_profile: str | None = None

    def select(self, name: str | None = None) -> RuntimeProfile:
        selected = name or self.default_profile
        if selected not in self.profiles:
            raise LaunchError("No runtime configured; add/select a runtime profile first.")
        return self.profiles[selected]


def config_path(override: str | None = None) -> Path:
    if override is not None:
        path = Path(override).expanduser().absolute()
        if path.name != "agent-console.local.toml":
            raise LaunchError("Custom config must be named agent-console.local.toml (Git ignored).")
        return path
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        setting = os.environ.get("XDG_CONFIG_HOME", "")
        base = Path(setting) if setting and Path(setting).is_absolute() else Path.home() / ".config"
    return base / "agent-console" / "config.toml"


PROFILE_FIELDS = {
    "python_executable",
    "ai_agent_main",
    "model",
    "provider",
    "default_verify",
    "default_max_retries",
}


def load_profiles(path: Path) -> ProfileBook:
    try:
        with path.open("rb") as stream:
            raw = stream.read(65537)
    except FileNotFoundError:
        return ProfileBook()
    except OSError:
        raise LaunchError("Cannot read runtime config.") from None
    try:
        if len(raw) > 65536:
            raise ValueError
        data = tomllib.loads(raw.decode("utf-8"))
        if set(data) - {"config_version", "default_profile", "profiles"}:
            raise ValueError
        if type(data.get("config_version")) is not int or data["config_version"] != 1:
            raise ValueError
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict) or len(profiles) > 20:
            raise ValueError
        book = ProfileBook(default_profile=data.get("default_profile"))
        for name, values in profiles.items():
            if not isinstance(values, dict) or set(values) - PROFILE_FIELDS:
                raise ValueError
            profile = RuntimeProfile(name=name, **values)
            profile.validate()
            book.profiles[name] = profile
        if book.default_profile is not None:
            identifier(book.default_profile, "default profile")
            book.select()
        return book
    except (ValueError, TypeError, UnicodeError):
        raise LaunchError(
            "Invalid runtime config; only documented profile fields are allowed."
        ) from None


def save_profiles(path: Path, book: ProfileBook) -> None:
    if len(book.profiles) > 20:
        raise LaunchError("At most 20 runtime profiles are supported.")
    lines = ["config_version = 1"]
    if book.default_profile is not None:
        book.select()
        lines.append(f"default_profile = {json.dumps(book.default_profile)}")
    for name, profile in book.profiles.items():
        profile.validate_files()
        if name != profile.name:
            raise LaunchError("Profile name does not match its config entry.")
        lines.append(f"\n[profiles.{json.dumps(name)}]")
        # Explicit fields only: never serialize UI state or arbitrary attributes.
        for key in sorted(PROFILE_FIELDS):
            lines.append(f"{key} = {json.dumps(getattr(profile, key), ensure_ascii=False)}")
    contents = ("\n".join(lines) + "\n").encode("utf-8")
    if len(contents) > 65536:
        raise LaunchError("Runtime config exceeds 64 KiB.")
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".profile-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        temporary.replace(path)
    except OSError:
        raise LaunchError("Cannot save runtime config.") from None
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
