"""Deterministic provenance helpers for bulk outputs."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    """Serialize a value deterministically for manifests and catalog columns."""

    return json.dumps(
        _json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def signature_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            _json_safe(payload), indent=2, sort_keys=True, allow_nan=False
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def write_text_atomic(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return path


def relative_paths(paths: Iterable[Path], root: Path) -> list[str]:
    result: list[str] = []
    for path in sorted(Path(item) for item in paths):
        try:
            result.append(path.relative_to(root).as_posix())
        except ValueError:
            result.append(path.as_posix())
    return result


__all__ = [
    "canonical_json",
    "relative_paths",
    "signature_sha256",
    "write_json_atomic",
    "write_text_atomic",
]
