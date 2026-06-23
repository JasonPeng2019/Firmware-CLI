from __future__ import annotations

from pyocd_debug_mcp.brain.playbooks import load_playbook_specs, select_playbook
from tests.harness import r11_benchmark as r11


def test_load_playbook_specs_finds_internal_turnkey_helpers() -> None:
    playbooks = load_playbook_specs()

    assert [item.playbook_id for item in playbooks] == [
        "nordic-recover-cycle",
        "reference-contract-diagnose",
        "reference-contract-repair",
        "reference-health-check",
    ]


def test_select_playbook_respects_board_scope() -> None:
    nordic = r11._load_board("nrf52833dk")
    stm32 = r11._load_board("nucleo_l476rg")

    assert select_playbook("nordic-recover-cycle", nordic).workflow_kind == "static_mcp_sequence"

    try:
        select_playbook("nordic-recover-cycle", stm32)
    except RuntimeError as exc:
        assert "not supported" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected the Nordic-only playbook to be refused on STM32")
