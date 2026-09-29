"""Backend-neutral remote collection access for production workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from posixpath import basename, dirname
import re
import shutil
import subprocess
from typing import Protocol, Sequence


class RemoteError(RuntimeError):
    """Base class for remote collection failures."""


class RemoteAuthenticationError(RemoteError):
    """The remote client is installed but not configured for access."""


class RemoteCommandError(RemoteError):
    """A remote client command returned a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        command: Sequence[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.command = tuple(command)
        self.returncode = int(returncode)
        self.stdout = stdout
        self.stderr = stderr


@dataclass(frozen=True)
class RemoteEntry:
    """One collection or data object returned by a remote backend."""

    path: str
    name: str
    is_collection: bool
    size_bytes: int | None = None
    checksum: str | None = None
    modified: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RemoteCollectionBackend(Protocol):
    """Storage operations required by the drone production orchestrator."""

    name: str

    def ensure_available(self) -> None:
        """Raise a useful error when the backend client is unavailable."""

    def verify_access(self, remote_path: str) -> None:
        """Verify configured authentication and access to ``remote_path``."""

    def list_directory(self, remote_path: str) -> list[RemoteEntry]:
        """List direct children of one remote collection."""

    def download_file(self, remote_path: str, local_path: Path) -> None:
        """Download one data object to an exact local path."""

    def path_exists(self, remote_path: str) -> bool:
        """Return whether a remote object or collection is accessible."""

    def upload_directory(self, local_path: Path, remote_parent: str) -> str:
        """Upload a directory beneath a remote parent and return its path."""


def normalize_remote_path(path: str) -> str:
    """Normalize separators while preserving the ``i:`` CyVerse prefix."""

    value = str(path).strip()
    if not value:
        raise ValueError("remote path cannot be empty")
    prefix = "i:" if value.startswith("i:") else ""
    body = value[2:] if prefix else value
    body = "/" + body.lstrip("/")
    body = re.sub(r"/{2,}", "/", body)
    if len(body) > 1:
        body = body.rstrip("/")
    return prefix + body


def remote_join(parent: str, child: str) -> str:
    """Join one child name to a normalized remote path."""

    parent_value = normalize_remote_path(parent)
    child_value = str(child).strip()
    if child_value.startswith("i:") or child_value.startswith("/"):
        prefix = "i:" if parent_value.startswith("i:") else ""
        return normalize_remote_path(
            child_value if child_value.startswith("i:") else prefix + child_value
        )
    return normalize_remote_path(parent_value + "/" + child_value)


def remote_relative_path(path: str, root: str) -> str:
    """Return a safe POSIX relative path beneath ``root``."""

    normalized = normalize_remote_path(path)
    normalized_root = normalize_remote_path(root)
    prefix = normalized_root.rstrip("/") + "/"
    if not normalized.startswith(prefix):
        raise ValueError(f"remote path {path!r} is outside source {root!r}")
    relative = normalized[len(prefix) :]
    if not relative or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise ValueError(f"unsafe remote relative path: {relative!r}")
    return relative


_COLLECTION_RE = re.compile(r"^\s*collection\s+(\S+)")
_DATA_RE = re.compile(r"^\s*data-object\s+(\S+)\s+(\d+)\b")


def parse_gocmd_listing(text: str, *, parent: str) -> list[RemoteEntry]:
    """Parse the stable collection/data-object lines emitted by ``gocmd ls``."""

    parent_value = normalize_remote_path(parent)
    entries: list[RemoteEntry] = []
    seen: set[tuple[str, bool]] = set()
    for raw_line in text.splitlines():
        collection_match = _COLLECTION_RE.match(raw_line)
        data_match = _DATA_RE.match(raw_line)
        if collection_match:
            token = collection_match.group(1)
            path = remote_join(parent_value, token)
            if path == parent_value:
                continue
            entry = RemoteEntry(
                path=path,
                name=basename(path[2:] if path.startswith("i:") else path),
                is_collection=True,
            )
        elif data_match:
            token, size = data_match.groups()
            path = remote_join(parent_value, token)
            entry = RemoteEntry(
                path=path,
                name=basename(path[2:] if path.startswith("i:") else path),
                is_collection=False,
                size_bytes=int(size),
            )
        else:
            continue
        key = (entry.path, entry.is_collection)
        if key not in seen:
            seen.add(key)
            entries.append(entry)
    return sorted(entries, key=lambda item: (not item.is_collection, item.path))


class GocmdRemoteBackend:
    """CyVerse backend using an existing non-interactive ``gocmd`` configuration."""

    name = "gocmd"

    def __init__(self, executable: str = "gocmd") -> None:
        self.executable = str(executable)

    def _command(self, *arguments: str) -> list[str]:
        return [self.executable, *map(str, arguments)]

    def _run(self, *arguments: str, operation: str) -> subprocess.CompletedProcess[str]:
        command = self._command(*arguments)
        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode:
            detail = (completed.stderr or completed.stdout or "").strip()
            lowered = detail.lower()
            error_type = (
                RemoteAuthenticationError
                if any(
                    marker in lowered
                    for marker in ("auth", "login", "credential", "configuration")
                )
                else RemoteCommandError
            )
            message = f"gocmd {operation} failed with exit code {completed.returncode}"
            if detail:
                message += f": {detail[-1200:]}"
            if error_type is RemoteAuthenticationError:
                raise RemoteAuthenticationError(
                    message
                    + ". Configure gocmd authentication outside SpectralBridge and retry."
                )
            raise RemoteCommandError(
                message,
                command=command,
                returncode=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        return completed

    def ensure_available(self) -> None:
        if shutil.which(self.executable) is None:
            raise RemoteError(
                f"gocmd executable {self.executable!r} is not available on PATH"
            )

    def verify_access(self, remote_path: str) -> None:
        self.ensure_available()
        self._run("ls", normalize_remote_path(remote_path), operation="access check")

    def list_directory(self, remote_path: str) -> list[RemoteEntry]:
        self.ensure_available()
        remote_path = normalize_remote_path(remote_path)
        completed = self._run("ls", remote_path, operation=f"listing {remote_path}")
        return parse_gocmd_listing(completed.stdout or "", parent=remote_path)

    def download_file(self, remote_path: str, local_path: Path) -> None:
        self.ensure_available()
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._run(
            "get",
            "--progress",
            normalize_remote_path(remote_path),
            str(local_path),
            operation=f"download of {remote_path}",
        )

    def path_exists(self, remote_path: str) -> bool:
        self.ensure_available()
        completed = subprocess.run(
            self._command("ls", normalize_remote_path(remote_path)),
            text=True,
            capture_output=True,
            check=False,
        )
        return completed.returncode == 0

    def upload_directory(self, local_path: Path, remote_parent: str) -> str:
        self.ensure_available()
        local_path = Path(local_path).resolve()
        if not local_path.is_dir():
            raise FileNotFoundError(f"upload directory does not exist: {local_path}")
        remote_parent = normalize_remote_path(remote_parent)
        destination = remote_join(remote_parent, local_path.name)
        if self.path_exists(destination):
            raise FileExistsError(
                f"remote result already exists; refusing to overwrite: {destination}"
            )
        self._run(
            "put",
            "--progress",
            str(local_path),
            remote_parent,
            operation=f"upload to {remote_parent}",
        )
        return destination


def remote_parent(path: str) -> str:
    """Return the parent of a normalized remote path."""

    value = normalize_remote_path(path)
    prefix = "i:" if value.startswith("i:") else ""
    body = value[2:] if prefix else value
    return normalize_remote_path(prefix + dirname(body))


__all__ = [
    "GocmdRemoteBackend",
    "RemoteAuthenticationError",
    "RemoteCollectionBackend",
    "RemoteCommandError",
    "RemoteEntry",
    "RemoteError",
    "normalize_remote_path",
    "parse_gocmd_listing",
    "remote_join",
    "remote_parent",
    "remote_relative_path",
]
