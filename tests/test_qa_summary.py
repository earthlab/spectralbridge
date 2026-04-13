from __future__ import annotations

from pathlib import Path

from spectralbridge.utils.qa_summary import build_drone_qa_summary


def test_build_drone_qa_summary_writes_scrollable_html(tmp_path: Path) -> None:
    scene_a = tmp_path / "AAA_20230814"
    scene_b = tmp_path / "BBB_20230815" / "nested"
    scene_a.mkdir(parents=True)
    scene_b.mkdir(parents=True)

    qa_a = scene_a / "AAA_20230814__qa.png"
    qa_b = scene_b / "BBB_20230815__qa.png"
    qa_a.write_bytes(b"png-a")
    qa_b.write_bytes(b"png-b")
    (scene_a / "AAA_20230814__polygons.parquet").write_text("parquet", encoding="utf-8")

    html_path = build_drone_qa_summary(tmp_path)

    assert html_path == tmp_path / "qa_summary.html"
    assert html_path.exists()

    html = html_path.read_text(encoding="utf-8")
    assert "Drone QA Summary" in html
    assert "AAA_20230814" in html
    assert "BBB_20230815" in html
    assert 'src="AAA_20230814/AAA_20230814__qa.png"' in html
    assert 'src="BBB_20230815/nested/BBB_20230815__qa.png"' in html
    assert 'href="AAA_20230814/AAA_20230814__polygons.parquet"' in html
