"""Helpers for building simple scrollable QA HTML summaries."""
from __future__ import annotations

from html import escape
from pathlib import Path


def _scene_name_from_png(path: Path) -> str:
    name = path.name
    if name.endswith("__qa.png"):
        return name[: -len("__qa.png")] or path.stem
    return path.stem


def _find_related_parquet(qa_png: Path, scene_name: str) -> Path | None:
    candidates = sorted(qa_png.parent.glob("*.parquet"))
    if not candidates:
        return None

    preferred_patterns = (
        f"{scene_name}__polygons.parquet",
        f"{scene_name}__merged.parquet",
        f"{scene_name}_merged_pixel_extraction.parquet",
        f"{scene_name}_polygons_merged_pixel_extraction.parquet",
    )
    for pattern in preferred_patterns:
        match = qa_png.parent / pattern
        if match.exists():
            return match

    for candidate in candidates:
        if candidate.stem.startswith(scene_name):
            return candidate
    return candidates[0]


def build_drone_qa_summary(
    base_dir: Path,
    output_html: Path | None = None,
    pattern: str = "*__qa.png",
) -> Path:
    """Build a local scrollable HTML page showing all drone QA PNGs under ``base_dir``.

    Example:
        ``build_drone_qa_summary(Path("drone_outputs"))``

    By default the summary is written to ``base_dir / "qa_summary.html"``.
    """

    base_dir = Path(base_dir).expanduser().resolve()
    if output_html is None:
        output_html = base_dir / "qa_summary.html"
    else:
        output_html = Path(output_html).expanduser().resolve()

    qa_pngs = sorted(
        (path for path in base_dir.rglob(pattern) if path.is_file()),
        key=lambda path: (path.name.lower(), str(path.parent).lower()),
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '  <meta charset="utf-8" />',
        "  <title>Drone QA Summary</title>",
        "  <style>",
        "    body { font-family: Arial, sans-serif; margin: 20px; background: #fafafa; color: #222; }",
        "    h1 { margin-bottom: 8px; }",
        "    p.meta { margin-top: 0; color: #555; }",
        "    .scene { margin-bottom: 40px; padding-bottom: 20px; border-bottom: 1px solid #ddd; }",
        "    .scene h2 { margin-bottom: 10px; }",
        "    .links { margin: 0 0 12px 0; font-size: 0.95rem; }",
        "    .links a { color: #0b57d0; text-decoration: none; margin-right: 16px; }",
        "    .links a:hover { text-decoration: underline; }",
        "    img { width: 100%; max-width: 1200px; height: auto; border: 1px solid #ccc; background: white; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Drone QA Summary</h1>",
        f"  <p class=\"meta\">Base directory: {escape(str(base_dir))} | Scenes: {len(qa_pngs)}</p>",
    ]

    if not qa_pngs:
        lines.append("  <p>No drone QA PNGs were found.</p>")
    else:
        for qa_png in qa_pngs:
            scene_name = _scene_name_from_png(qa_png)
            img_rel = escape(str(qa_png.relative_to(output_html.parent)))
            parquet_path = _find_related_parquet(qa_png, scene_name)
            lines.append('  <div class="scene">')
            lines.append(f"    <h2>{escape(scene_name)}</h2>")
            lines.append('    <div class="links">')
            lines.append(f'      <a href="{img_rel}">Open PNG</a>')
            if parquet_path is not None:
                parquet_rel = escape(str(parquet_path.relative_to(output_html.parent)))
                lines.append(f'      <a href="{parquet_rel}">Parquet</a>')
            lines.append("    </div>")
            lines.append(
                f'    <img src="{img_rel}" alt="{escape(scene_name)} QA plot" loading="lazy" />'
            )
            lines.append("  </div>")

    lines.extend(["</body>", "</html>"])
    output_html.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_html


__all__ = ["build_drone_qa_summary"]
