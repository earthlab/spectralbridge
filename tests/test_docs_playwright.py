"""Browser smoke tests for the built MkDocs site."""

from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse

import pytest


pytestmark = pytest.mark.playwright

MARKDOWN_IN_HTML_ROUTES = (
    "api/",
    "concepts/why-calibration/",
    "faq/",
    "pipeline/outputs/",
    "pipeline/qa/",
    "pipeline/qa_panel/",
    "pipeline/stages/",
    "quickstart/",
    "reference/configuration/",
    "reference/schemas/",
    "reference/validation/",
    "troubleshooting/",
    "tutorials/cloud-workflow/",
    "usage/cli/",
    "usage/parquet/",
)
GITHUB_NOTEBOOK_BASE = (
    "https://github.com/earthlab/spectralbridge/blob/main/"
    "docs/vignettes/notebooks/"
)


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

            assert page.get_by_role(
                "heading", name="Three technical views. Read them one at a time."
            ).is_visible()
            assert page.locator(".sb-science-panel").count() == 3
            assert page.locator(".sb-science-panel__figure svg").count() == 3
            assert page.locator(
                "a[href$='images/homepage/spectralbridge-technical-overview.png']"
            ).count() == 3
            desktop_figure = page.locator(".sb-science-panel__figure").first
            assert desktop_figure.bounding_box()["width"] > 500

            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            mobile_viewport = page.locator(".sb-science-panel__viewport").first
            assert mobile_viewport.evaluate(
                "element => element.scrollWidth > element.clientWidth"
            )
            page.set_viewport_size({"width": 1280, "height": 900})

            page.goto(urljoin(base_url, "vignettes/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Choose a vignette").is_visible()
            assert page.get_by_role(
                "link",
                name="Carry On My Wayward Son (resume a run)",
            ).is_visible()
            assert page.get_by_role(
                "link",
                name="7. Extract polygon spectra",
            ).is_visible()

            page.goto(
                urljoin(base_url, "vignettes/notebook-vignettes/"),
                wait_until="networkidle",
            )
            assert page.get_by_role(
                "heading", name="Runnable notebook vignettes"
            ).is_visible()
            notebook_links = page.locator(
                f"a[href^='{GITHUB_NOTEBOOK_BASE}'][href$='.ipynb']"
            )
            assert notebook_links.count() == 10
            assert page.get_by_role(
                "link", name="Correct NEON reflectance", exact=True
            ).get_attribute("href") == (
                f"{GITHUB_NOTEBOOK_BASE}02_correct_neon.ipynb"
            )

            page.goto(urljoin(base_url, "reference/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Technical reference map").is_visible()
            assert page.get_by_role("link", name="Stage order and restart behavior").first.is_visible()

            page.goto(urljoin(base_url, "validation/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Validation evidence").is_visible()
            assert page.get_by_role("link", name="Topographic correction").first.is_visible()
            assert page.get_by_text("offline-contract-5-per-module").first.is_visible()

            page.goto(
                urljoin(base_url, "validation/topographic_correction/"),
                wait_until="networkidle",
            )
            assert page.get_by_role(
                "heading", name="Validation: Topographic correction"
            ).is_visible()
            assert page.get_by_text("topographic_correction-005").is_visible()
            assert page.get_by_role(
                "cell", name="Before minus after correlation.", exact=True
            ).is_visible()

            page.goto(urljoin(base_url, "pipeline/outputs/"), wait_until="networkidle")
            assert page.get_by_role("heading", name="Outputs & File Structure").is_visible()
            assert page.get_by_text("_merged_pixel_extraction.parquet").first.is_visible()

            for route in MARKDOWN_IN_HTML_ROUTES:
                page.goto(urljoin(base_url, route), wait_until="networkidle")
                assert page.locator(".sb-doc-page").count() == 1, route
                assert page.locator(".sb-doc-hero .sb-kicker").count() == 1, route
                assert '<p class="sb-kicker">' not in page.locator(
                    "article.md-content__inner"
                ).inner_text(), route

            page.goto(urljoin(base_url, "faq/"), wait_until="networkidle")
            assert page.get_by_role(
                "heading", name="Frequently asked questions"
            ).is_visible()
            assert page.locator(".sb-doc-hero .sb-doc-card").count() == 3
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            assert page.locator(".sb-doc-hero .sb-doc-card").first.is_visible()
            page.set_viewport_size({"width": 1280, "height": 900})

            page.goto(
                urljoin(base_url, "tutorials/cloud-workflow/"),
                wait_until="networkidle",
            )
            assert page.get_by_role(
                "heading", name="Cloud and HPC workflows"
            ).is_visible()
            assert page.locator(".sb-doc-hero .sb-doc-card").count() == 3
            assert '<p class="sb-kicker">Tutorial</p>' not in page.locator(
                "article.md-content__inner"
            ).inner_text()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            assert page.locator(".sb-doc-hero .sb-doc-card").first.is_visible()
            page.set_viewport_size({"width": 1280, "height": 900})

            page.goto(base_url, wait_until="networkidle")
            search_query = page.locator("[data-md-component='search-query']").first
            search_query.click()
            search_query.fill("Parquet")
            assert search_query.input_value() == "Parquet"

            search_index = page.evaluate(
                """async () => {
                    const url = new URL("search/search_index.json", document.baseURI);
                    const response = await fetch(url);
                    if (!response.ok) throw new Error(`Search index: ${response.status}`);
                    return response.json();
                }"""
            )
            assert any(
                "parquet" in f"{document.get('title', '')} {document.get('text', '')}".lower()
                for document in search_index["docs"]
            )
        finally:
            browser.close()

    assert page_errors == []
    assert console_errors == []
    assert failed_assets == []
