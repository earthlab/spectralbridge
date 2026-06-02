"""Browser smoke tests for the built MkDocs site."""

from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

import pytest


pytestmark = pytest.mark.playwright


def _docs_site_url() -> str:
    url = os.getenv("SPECTRALBRIDGE_DOCS_SITE")
    if not url:
        pytest.skip("Set SPECTRALBRIDGE_DOCS_SITE to run docs browser smoke tests.")
    return url.rstrip("/") + "/"


def _collect_page_health(page, base_url: str) -> tuple[list[str], list[str], list[str]]:
    parsed_base = urlparse(base_url)
    page_errors: list[str] = []
    console_errors: list[str] = []
    failed_assets: list[str] = []

    def _same_origin(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme == parsed_base.scheme and parsed.netloc == parsed_base.netloc

    page.on("pageerror", lambda exc: page_errors.append(str(exc)))
    page.on(
        "console",
        lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
    )
    page.on(
        "response",
        lambda response: failed_assets.append(
            f"{response.status} {response.request.resource_type} {response.url}"
        )
        if response.status >= 400 and _same_origin(response.url)
        else None,
    )

    return page_errors, console_errors, failed_assets


def test_docs_site_core_pages_render_in_browser() -> None:
    base_url = _docs_site_url()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - depends on local environment
        raise AssertionError(
            "Playwright is required for docs browser smoke tests. "
            "Install pytest-playwright/playwright and Chromium."
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors, console_errors, failed_assets = _collect_page_health(page, base_url)

        try:
            page.goto(base_url, wait_until="networkidle")
            assert "SpectralBridge" in page.title()
            assert page.locator("h1#spectralbridge").is_visible()

            logo = page.locator("img[alt='SpectralBridge logo']").first
            assert logo.evaluate("(img) => img.naturalWidth") > 0

            page.goto(urljoin(base_url, "quickstart/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Quickstart").is_visible()

            page.goto(urljoin(base_url, "pipeline/outputs/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Outputs & File Structure").is_visible()
            assert page.get_by_text("_merged_pixel_extraction.parquet").first.is_visible()

            page.goto(base_url, wait_until="networkidle")
            search_query = page.locator("[data-md-component='search-query']").first
            search_query.click()
            search_query.fill("Parquet")
            page.wait_for_selector(".md-search-result__link", timeout=5000)
            assert page.locator(".md-search-result__link").first.is_visible()
        finally:
            browser.close()

    assert page_errors == []
    assert console_errors == []
    assert failed_assets == []
