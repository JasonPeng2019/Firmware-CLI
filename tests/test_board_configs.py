from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = REPO_ROOT / "boards"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stage0_check import load_board_configs_from_paths


def test_all_tracked_board_configs_load() -> None:
    paths = sorted(
        path
        for path in BOARD_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml"}
    )
    boards = load_board_configs_from_paths(paths)

    assert boards, "expected at least one board config"
    assert len(boards) == len(paths)
    assert len({board.board_id for board in boards}) == len(boards)

    boards_by_source = {board.source_path.name: board for board in boards if board.source_path}
    assert set(boards_by_source) == {path.name for path in paths}

    for filename, expected_board_id in {
        "nrf52833dk.yaml": "nrf52833dk",
        "nrf52840dk.yaml": "nrf52840dk",
        "nucleo_l476rg.yaml": "nucleo_l476rg",
    }.items():
        assert boards_by_source[filename].board_id == expected_board_id


def test_nrf52833_board_profile_has_exact_identity_check() -> None:
    [board] = load_board_configs_from_paths([BOARD_DIR / "nrf52833dk.yaml"])

    assert board.board_id == "nrf52833dk"
    assert board.pyocd_target == "nrf52833"
    assert board.probe_family == "jlink"
    assert board.silicon_id_addr == 0x10000100
    assert board.silicon_id_expected == 0x00052833
    assert board.silicon_id_label == "FICR.INFO.PART"
