from pathlib import Path

import move_folders_from_instance_to_remote as helper
from move_folders_from_instance_to_remote import _remote_parent_chain


def test_remote_parent_chain_for_nested_qa_folder() -> None:
    assert _remote_parent_chain(
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/"
        "YELL_n01/NEON_D12_YELL_DP1_L033-1_20230715_directional_reflectance/"
        "qa/stages/00_acquisition"
    ) == [
        "i:/iplant",
        "i:/iplant/home",
        "i:/iplant/home/shared",
        "i:/iplant/home/shared/earthlab",
        "i:/iplant/home/shared/earthlab/macrosystems",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/YELL_n01",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/YELL_n01/NEON_D12_YELL_DP1_L033-1_20230715_directional_reflectance",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/YELL_n01/NEON_D12_YELL_DP1_L033-1_20230715_directional_reflectance/qa",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/YELL_n01/NEON_D12_YELL_DP1_L033-1_20230715_directional_reflectance/qa/stages",
        "i:/iplant/home/shared/earthlab/macrosystems/Aug_2026_Processed_Flightlines/YELL_n01/NEON_D12_YELL_DP1_L033-1_20230715_directional_reflectance/qa/stages/00_acquisition",
    ]


def test_remote_parent_chain_handles_rootish_paths() -> None:
    assert _remote_parent_chain("i:/iplant") == ["i:/iplant"]


def test_reset_failure_log_replaces_previous_run(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "gocmd_upload_failures.log"
    log_path.write_text("old failure\n", encoding="utf-8")
    monkeypatch.setattr(helper, "FAILURE_LOG", Path(log_path))

    helper.reset_failure_log()

    assert not log_path.exists()
