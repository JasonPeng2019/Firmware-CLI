from __future__ import annotations

from pathlib import Path

from stage0_check import load_board_configs_from_paths


REPO_ROOT = Path(__file__).resolve().parents[1]
BOARD_DIR = REPO_ROOT / "boards"


def test_all_tracked_board_configs_load() -> None:
    paths = sorted(path for path in BOARD_DIR.glob("*.ya?ml"))
    boards = load_board_configs_from_paths(paths)

    assert boards, "expected at least one board config"
    assert {board.board_id for board in boards} == {path.stem for path in paths}


def test_nrf52833_board_profile_has_exact_identity_check() -> None:
    [board] = load_board_configs_from_paths([BOARD_DIR / "nrf52833dk.yaml"])

    assert board.board_id == "nrf52833dk"
    assert board.pyocd_target == "nrf52833"
    assert board.probe_family == "jlink"
    assert board.silicon_id_addr == 0x10000100
    assert board.silicon_id_expected == 0x00052833
    assert board.silicon_id_label == "FICR.INFO.PART"
