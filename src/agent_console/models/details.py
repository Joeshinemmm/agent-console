"""Narrow public metadata projection. Free-form payloads never enter event state."""

import re
from dataclasses import dataclass

# Engine names that llm.* events report in metadata.provider; other values are dropped.
PROVIDERS = ("codex", "claude")


def relative_path(value: object) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 240:
        return None
    value = value.replace("\\", "/")
    if not re.fullmatch(r"[A-Za-z0-9._ /-]+", value):
        return None
    if any(part in ("", ".", "..") or part.endswith((" ", ".")) for part in value.split("/")):
        return None
    if re.search(
        r"(?i)(\.env|auth\.json|credential|password|secret|token|cookie|authorization|api[_-]?key|sk-|ghp_)",
        value,
    ):
        return None
    return value


@dataclass(frozen=True, slots=True)
class EventDetails:
    external: bool | None = None
    git_repository: bool | None = None
    git_dirty: bool | None = None
    path: str | None = None
    provider: str | None = None

    @classmethod
    def from_metadata(cls, event_type: str, metadata: dict) -> "EventDetails":
        def flag(name: str) -> bool | None:
            value = metadata.get(name)
            return value if type(value) is bool else None

        if event_type == "workspace.validated":
            return cls(external=flag("external"))
        if event_type == "git.status":
            return cls(git_repository=flag("git_repository"), git_dirty=flag("dirty"))
        if event_type in ("file.created", "file.modified", "file.deleted"):
            return cls(path=relative_path(metadata.get("path")))
        if event_type.startswith("llm."):
            # Session identifiers (thread_id, auth_type, continuation) are never retained.
            value = metadata.get("provider")
            return cls(provider=value if isinstance(value, str) and value in PROVIDERS else None)
        return cls()
