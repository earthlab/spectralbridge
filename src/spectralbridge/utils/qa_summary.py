"""Helpers for building lightweight aggregate drone QA summaries."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


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
    """Build a multi-page PDF showing all drone QA PNGs under ``base_dir``.

    Example:
        ``build_drone_qa_summary(Path("drone_outputs"))``

    By default the summary is written to ``base_dir / "qa_summary.pdf"``.
    """

    base_dir = Path(base_dir).expanduser().resolve()
    if output_html is None:
        output_pdf = base_dir / "qa_summary.pdf"
    else:
        output_pdf = Path(output_html).expanduser().resolve()

    qa_pngs = sorted(
        (path for path in base_dir.rglob(pattern) if path.is_file()),
        key=lambda path: (path.name.lower(), str(path.parent).lower()),
    )

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output_pdf) as pdf:
        if not qa_pngs:
            fig = plt.figure(figsize=(11, 8.5))
            fig.text(0.08, 0.90, "Drone QA Summary", fontsize=18, weight="bold")
            fig.text(0.08, 0.84, f"Base directory: {base_dir}", fontsize=11)
            fig.text(0.08, 0.74, "No drone QA PNGs were found.", fontsize=13)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
        else:
            for qa_png in qa_pngs:
                scene_name = _scene_name_from_png(qa_png)
                parquet_path = _find_related_parquet(qa_png, scene_name)
                image = plt.imread(qa_png)

                fig = plt.figure(figsize=(11, 14))
                fig.text(0.05, 0.975, "Drone QA Summary", fontsize=16, weight="bold", va="top")
                fig.text(0.05, 0.948, scene_name, fontsize=13, weight="bold", va="top")
                fig.text(0.05, 0.928, f"QA PNG: {qa_png.relative_to(base_dir)}", fontsize=9, va="top")
                if parquet_path is not None:
                    fig.text(
                        0.05,
                        0.910,
                        f"Parquet: {parquet_path.relative_to(base_dir)}",
                        fontsize=9,
                        va="top",
                    )

                ax = fig.add_axes([0.05, 0.05, 0.90, 0.84])
                ax.imshow(image)
                ax.axis("off")

                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

    return output_pdf


__all__ = ["build_drone_qa_summary"]
