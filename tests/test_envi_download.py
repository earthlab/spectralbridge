from __future__ import annotations

from pathlib import Path

import pytest
import requests

from spectralbridge.envi_download import download_neon_file


class _Response:
    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {"data": {"files": []}}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self, response: _Response) -> None:
        self.response = response
        self.headers: dict[str, str] = {}
        self.trust_env = True

    def get(self, url: str, *, stream: bool = False, timeout: int = 60) -> _Response:
        del url, stream, timeout
        return self.response


def test_download_uses_neon_api_token_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _Session(_Response())
    monkeypatch.setenv("NEON_API_TOKEN", "test-token")

    with pytest.raises(FileNotFoundError, match="No HDF5 file found"):
        download_neon_file(
            "NIWO",
            "DP1.30006.001",
            "2023-08",
            "flight",
            tmp_path,
            session=session,  # type: ignore[arg-type]
        )

    assert session.headers == {"X-API-Token": "test-token"}


def test_download_explains_missing_token_on_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Forbidden(_Response):
        status_code = 403

        def raise_for_status(self) -> None:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.exceptions.HTTPError("forbidden", response=response)

    monkeypatch.delenv("NEON_API_TOKEN", raising=False)
    monkeypatch.delenv("NEON_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="requires an API token"):
        download_neon_file(
            "NIWO",
            "DP1.30006.001",
            "2023-08",
            "flight",
            tmp_path,
            session=_Session(_Forbidden()),  # type: ignore[arg-type]
        )


def test_download_proxy_retry_uses_requests_exception_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _RetrySession(_Session):
        def __init__(self) -> None:
            super().__init__(_Response())
            self.calls = 0

        def get(self, url: str, *, stream: bool = False, timeout: int = 60) -> _Response:
            del url, stream, timeout
            self.calls += 1
            if self.calls == 1:
                raise requests.exceptions.ProxyError("proxy unavailable")
            return self.response

    monkeypatch.delenv("NEON_API_TOKEN", raising=False)
    monkeypatch.delenv("NEON_TOKEN", raising=False)
    session = _RetrySession()
    monkeypatch.setattr(requests, "Session", lambda: session)

    with pytest.raises(FileNotFoundError, match="No HDF5 file found"):
        download_neon_file(
            "NIWO",
            "DP1.30006.001",
            "2023-08",
            "flight",
            tmp_path,
        )

    assert session.calls == 2
    assert session.trust_env is False
