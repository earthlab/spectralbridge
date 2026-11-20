"""Review case selection is geometric and never assigns a new PFT label."""

import importlib
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "examples/publication_figures")
)
review = importlib.import_module("prepare_landsat_pixel_review")
sys.path.pop(0)


def test_examples_select_retained_interior_boundary_and_unretained_cover():
    a = pd.DataFrame(
        dict(
            candidate_id=["a", "b"],
            nominal_target_fraction=[0.99, 0.951],
            source_kernel_target_fraction=[0.97, 0.4],
        )
    )
    all_cells = pd.concat(
        [
            a.assign(nominal_95pct=True),
            pd.DataFrame(
                dict(
                    candidate_id=["r", "s"],
                    nominal_target_fraction=[0.949, 0.2],
                    source_kernel_target_fraction=[0.5, 0.1],
                    nominal_95pct=[False, False],
                )
            ),
        ],
        ignore_index=True,
    )
    examples = review.choose_examples(a, all_cells)
    assert [r.candidate_id for _, r in examples] == ["a", "b", "r"]
    assert examples[2][1].nominal_target_fraction < 0.95


def test_single_retained_cell_and_no_rejected_cell_are_explicit():
    a = pd.DataFrame(
        dict(
            candidate_id=["a"],
            nominal_target_fraction=[1.0],
            source_kernel_target_fraction=[0.96],
        )
    )
    e = review.choose_examples(a, a.assign(nominal_95pct=True))
    assert e[0][1].candidate_id == e[1][1].candidate_id
    assert e[2][1] is None


def test_reproduction_preserves_reviewer_decisions(tmp_path):
    fields = [
        "reviewer",
        "team_decision",
        "revised_pft",
        "confidence",
        "issue_tags",
        "review_notes",
    ]
    new = pd.DataFrame(
        {
            "review_id": ["P01-C01"],
            "candidate_id": ["candidate"],
            **{f: [""] for f in fields},
        }
    )
    old = new.copy()
    old.loc[0, "reviewer"] = "team"
    old.loc[0, "team_decision"] = "Defer"
    old.loc[0, "review_notes"] = "Shadow unresolved"
    path = tmp_path / "reviews.csv"
    old.to_csv(path, index=False)
    actual = review.preserve_team_reviews(new, path)
    assert actual.loc[0, "review_notes"] == "Shadow unresolved"
    assert actual.loc[0, "team_decision"] == "Defer"
