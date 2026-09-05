"""Extensible scientific-identity parsing for bulk flightline discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Protocol, Sequence

from spectralbridge.file_types import NEONReflectanceFile


@dataclass(frozen=True)
class FlightlineIdentity:
    """Scientific identity for one independently processed flightline."""

    flightline_id: str
    site: str | None
    acquisition_date: str | None
    identity_source: str


class FlightlineIdentityParser(Protocol):
    """Protocol for adding identity conventions without changing discovery."""

    name: str

    def parse(self, directory: Path) -> FlightlineIdentity | None:
        """Return an identity when ``directory`` matches this convention."""


@dataclass(frozen=True)
class ManifestIdentityParser:
    """Parse a generic, user-authored flightline identity manifest."""

    filename: str = "spectralbridge_flightline.json"
    name: str = "spectralbridge_flightline_manifest"

    def parse(self, directory: Path) -> FlightlineIdentity | None:
        manifest = directory / self.filename
        if not manifest.is_file():
            return None
        if manifest.stat().st_size > 1024 * 1024:
            raise ValueError(f"identity manifest is unexpectedly large: {manifest}")
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"unreadable identity manifest: {manifest}") from exc
        flightline_id = payload.get("flightline_id")
        if not isinstance(flightline_id, str) or not flightline_id.strip():
            raise ValueError(f"identity manifest has no flightline_id: {manifest}")
        acquisition_date = payload.get("acquisition_date")
        if acquisition_date is not None:
            try:
                acquisition_date = datetime.strptime(
                    str(acquisition_date), "%Y-%m-%d"
                ).date().isoformat()
            except ValueError as exc:
                raise ValueError(
                    f"identity manifest has invalid acquisition_date: {manifest}"
                ) from exc
        site = payload.get("site")
        return FlightlineIdentity(
            flightline_id=flightline_id.strip(),
            site=str(site).strip() if site is not None else None,
            acquisition_date=acquisition_date,
            identity_source=self.name,
        )


@dataclass(frozen=True)
class NEONDirectoryIdentityParser:
    """Preserve canonical NEON-directory support as one parser plugin."""

    name: str = "canonical_neon_directory"

    def parse(self, directory: Path) -> FlightlineIdentity | None:
        try:
            parsed = NEONReflectanceFile.from_filename(f"{directory.name}.h5")
        except ValueError:
            return None
        acquisition_date = None
        if parsed.date:
            acquisition_date = datetime.strptime(parsed.date, "%Y%m%d").date().isoformat()
        return FlightlineIdentity(
            flightline_id=directory.name,
            site=parsed.site,
            acquisition_date=acquisition_date,
            identity_source=self.name,
        )


DEFAULT_IDENTITY_PARSERS: tuple[FlightlineIdentityParser, ...] = (
    ManifestIdentityParser(),
    NEONDirectoryIdentityParser(),
)


def resolve_flightline_identity(
    directory: str | Path,
    *,
    parsers: Sequence[FlightlineIdentityParser] = DEFAULT_IDENTITY_PARSERS,
) -> FlightlineIdentity | None:
    """Resolve one directory, rejecting conflicting parser results."""

    path = Path(directory)
    matches = [identity for parser in parsers if (identity := parser.parse(path))]
    if not matches:
        return None
    scientific_ids = {identity.flightline_id for identity in matches}
    if len(scientific_ids) > 1:
        raise ValueError(
            f"identity parsers disagree for {path}: {sorted(scientific_ids)}"
        )
    return matches[0]


__all__ = [
    "DEFAULT_IDENTITY_PARSERS",
    "FlightlineIdentity",
    "FlightlineIdentityParser",
    "ManifestIdentityParser",
    "NEONDirectoryIdentityParser",
    "resolve_flightline_identity",
]
