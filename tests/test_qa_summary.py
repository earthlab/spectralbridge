from __future__ import annotations

from pathlib import Path

from spectralbridge.utils.qa_summary import build_drone_qa_summary


def test_build_drone_qa_summary_writes_pdf(tmp_path: Path) -> None:
    scene_a = tmp_path / "AAA_20230814"
    scene_b = tmp_path / "BBB_20230815" / "nested"
    scene_a.mkdir(parents=True)
    scene_b.mkdir(parents=True)

    qa_a = scene_a / "AAA_20230814__qa.png"
    qa_b = scene_b / "BBB_20230815__qa.png"
    qa_a.write_bytes(b"png-a")
    qa_b.write_bytes(b"png-b")
    (scene_a / "AAA_20230814__polygons.parquet").write_text("parquet", encoding="utf-8")

    pdf_path = build_drone_qa_summary(tmp_path)

    assert pdf_path == tmp_path / "qa_summary.pdf"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
