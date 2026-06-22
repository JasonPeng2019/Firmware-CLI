"""Targeted tests for the turnkey brain."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyocd_debug_mcp.board_config import DEFAULT_BOARD_CONFIG_DIR, load_selected_board_configs
from pyocd_debug_mcp.brain import runner as runner_module
from pyocd_debug_mcp.brain.cli import main
from pyocd_debug_mcp.brain.models import ToolCallResponse, TurnkeyRunRequest
from pyocd_debug_mcp.brain.runner import TurnkeyRunner
from pyocd_debug_mcp.brain.skills import SkillConfigError, load_skill_specs, render_template, select_skill

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeToolClient:
    def __init__(self, responses: dict[str, ToolCallResponse | list[ToolCallResponse]]) -> None:
        self._responses: dict[str, list[ToolCallResponse]] = {}
        for name, response in responses.items():
            if isinstance(response, list):
                self._responses[name] = list(response)
            else:
                self._responses[name] = [response]
        self.calls: list[tuple[str, dict[str, object] | None, float]] = []

    async def list_tool_names(self) -> set[str]:
        return set(self._responses)

    async def call_tool_text(
        self,
        name: str,
        arguments: dict[str, object] | None,
        *,
        timeout_seconds: float,
    ) -> ToolCallResponse:
        self.calls.append((name, arguments, timeout_seconds))
        queue = self._responses.get(name)
        if not queue:
            raise AssertionError(f"Unexpected tool call: {name}")
        return queue.pop(0)


def _board(board_id: str):
    boards = load_selected_board_configs(DEFAULT_BOARD_CONFIG_DIR, requested_ids=[board_id])
    return boards[0]


def test_load_skill_specs_reads_tracked_phase1_and_phase2_skills() -> None:
    skills = load_skill_specs()
    assert {skill.skill_id for skill in skills} >= {
        "reference-health-check",
        "nordic-recover-cycle",
        "reference-contract-diagnose",
        "reference-contract-repair",
    }


def test_select_skill_blocks_unsupported_board() -> None:
    board = _board("nucleo_l476rg")
    with pytest.raises(SkillConfigError):
        select_skill("nordic-recover-cycle", board)


def test_render_template_formats_nested_values() -> None:
    rendered = render_template(
        {
            "path": "{flash_artifact}",
            "nested": ["prefix", "{board_id}"],
        },
        {
            "flash_artifact": "C:/tmp/fw.hex",
            "board_id": "nrf52840dk",
        },
    )
    assert rendered == {
        "path": "C:/tmp/fw.hex",
        "nested": ["prefix", "nrf52840dk"],
    }


@pytest.mark.asyncio
async def test_runner_executes_static_skill_and_records_session(tmp_path: Path) -> None:
    runner = TurnkeyRunner(result_root=tmp_path)
    client = FakeToolClient(
        {
            "connect": ToolCallResponse(
                text="Connected to board [board config: nrf52840dk] via pyocd-native; session_id=abc123",
                is_error=False,
            ),
            "get_board_info": ToolCallResponse(text="board info", is_error=False),
            "flash_firmware": ToolCallResponse(
                text="Flashed C:/tmp/fw.hex via pyocd-native; target left halted.",
                is_error=False,
            ),
            "read_core_register": ToolCallResponse(text="0x08000100", is_error=False),
            "read_symbol_u32": ToolCallResponse(
                text=(
                    "Symbol stage1_known_value from C:/tmp/fw.elf "
                    "@0x20000000 size=4 type=STT_OBJECT value_u32=0x1234ABCD"
                ),
                is_error=False,
            ),
            "resume": ToolCallResponse(text="Target resumed.", is_error=False),
            "read_serial": ToolCallResponse(
                text="UART matched on COM1 at 115200 baud via pyocd-native; expected='boot ok'; excerpt=boot ok",
                is_error=False,
            ),
            "disconnect": ToolCallResponse(text="Disconnected.", is_error=False),
        }
    )

    result = await runner.run_with_client(
        TurnkeyRunRequest(board_id="nrf52840dk", skill_id="reference-health-check"),
        client,
    )

    assert result.final_status == "success"
    assert result.classification == "healthy"
    assert result.session_id == "abc123"
    assert Path(result.result_path or "").exists()
    assert [call[0] for call in client.calls] == [
        "connect",
        "get_board_info",
        "flash_firmware",
        "read_core_register",
        "read_symbol_u32",
        "resume",
        "read_serial",
        "disconnect",
    ]


@pytest.mark.asyncio
async def test_runner_reference_contract_diagnose_classifies_halted_uart(tmp_path: Path) -> None:
    runner = TurnkeyRunner(result_root=tmp_path)
    client = FakeToolClient(
        {
            "connect": ToolCallResponse(
                text="Connected to board 'nrf52840dk' via probe 123 via pyocd-native. session_id=diag001",
                is_error=False,
            ),
            "flash_firmware": ToolCallResponse(
                text="Flashed C:/tmp/fw.hex via pyocd-native; target left halted.",
                is_error=False,
            ),
            "get_state": ToolCallResponse(text="HALTED", is_error=False),
            "read_symbol_u32": ToolCallResponse(
                text=(
                    "Symbol stage1_known_value from C:/tmp/fw.elf "
                    "@0x20000000 size=4 type=STT_OBJECT value_u32=0x1234ABCD"
                ),
                is_error=False,
            ),
            "read_serial": ToolCallResponse(
                text=(
                    "UART did not match on COM1 at 115200 baud via pyocd-native; "
                    "expected='boot ok'; excerpt=(none)"
                ),
                is_error=False,
            ),
            "disconnect": ToolCallResponse(text="Disconnected.", is_error=False),
        }
    )

    result = await runner.run_with_client(
        TurnkeyRunRequest(
            board_id="nrf52840dk",
            skill_id="reference-contract-diagnose",
            initial_post_flash_state="halted",
        ),
        client,
    )

    assert result.final_status == "diagnosed_only"
    assert result.classification == "observability_fault"
    assert result.root_cause is not None and "halted" in result.root_cause
    assert result.files_changed == ()
    assert result.verification["symbol_ok"] is True
    assert result.verification["uart_ok"] is False


@pytest.mark.asyncio
async def test_runner_reference_contract_repair_restores_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src" / "src").mkdir(parents=True)
    (workspace_root / "build").mkdir(parents=True)

    bug_main = (
        REPO_ROOT
        / "firmware"
        / "nrf52840dk"
        / "bugs"
        / "b001__wrong_boot_text"
        / "src"
        / "src"
        / "main.c"
    ).read_text(encoding="utf-8")
    reference_main_path = (
        REPO_ROOT / "firmware" / "nrf52840dk" / "reference" / "src" / "src" / "main.c"
    )
    reference_main = reference_main_path.read_text(encoding="utf-8")
    target_main = workspace_root / "src" / "src" / "main.c"
    target_main.write_text(bug_main, encoding="utf-8")
    (workspace_root / "build" / "firmware.hex").write_text("hex", encoding="utf-8")
    (workspace_root / "build" / "firmware.elf").write_text("elf", encoding="utf-8")

    monkeypatch.setattr(
        runner_module,
        "_run_local_command",
        lambda command, *, cwd, timeout_seconds=1800.0: "west build ok",
    )

    runner = TurnkeyRunner(result_root=tmp_path / "results")
    client = FakeToolClient(
        {
            "connect": ToolCallResponse(
                text="Connected to board 'nrf52840dk' via probe 123 via pyocd-native. session_id=fix001",
                is_error=False,
            ),
            "flash_firmware": [
                ToolCallResponse(
                    text="Flashed C:/tmp/fw.hex via pyocd-native; target left running.",
                    is_error=False,
                ),
                ToolCallResponse(
                    text="Flashed C:/tmp/fw.hex via pyocd-native; target left running.",
                    is_error=False,
                ),
            ],
            "get_state": [
                ToolCallResponse(text="RUNNING", is_error=False),
                ToolCallResponse(text="RUNNING", is_error=False),
            ],
            "read_symbol_u32": [
                ToolCallResponse(
                    text=(
                        "Symbol stage1_known_value from C:/tmp/fw.elf "
                        "@0x20000000 size=4 type=STT_OBJECT value_u32=0x1234ABCD"
                    ),
                    is_error=False,
                ),
                ToolCallResponse(
                    text=(
                        "Symbol stage1_known_value from C:/tmp/fw.elf "
                        "@0x20000000 size=4 type=STT_OBJECT value_u32=0x1234ABCD"
                    ),
                    is_error=False,
                ),
            ],
            "read_serial": [
                ToolCallResponse(
                    text=(
                        "UART did not match on COM1 at 115200 baud via pyocd-native; "
                        "expected='boot ok'; excerpt=boot nope"
                    ),
                    is_error=False,
                ),
                ToolCallResponse(
                    text=(
                        "UART matched on COM1 at 115200 baud via pyocd-native; "
                        "expected='boot ok'; excerpt=boot ok"
                    ),
                    is_error=False,
                ),
            ],
            "disconnect": ToolCallResponse(text="Disconnected.", is_error=False),
        }
    )

    result = await runner.run_with_client(
        TurnkeyRunRequest(
            board_id="nrf52840dk",
            skill_id="reference-contract-repair",
            workspace_root=str(workspace_root),
            flash_artifact="build/firmware.hex",
            symbol_artifact="build/firmware.elf",
            build_command="uv run pyocd-zephyr-build --app-dir src --build-dir build --board nrf52840dk/nrf52840",
        ),
        client,
    )

    assert result.final_status == "fixed"
    assert result.classification == "code_bug"
    assert result.files_changed == ("src/src/main.c",)
    assert result.verification["green_check_ok"] is True
    assert result.observations
    assert result.hypotheses
    assert result.experiments
    assert result.strategy_evaluations
    assert target_main.read_text(encoding="utf-8") == reference_main
    assert Path(result.result_path or "").exists()


def test_cli_list_skills_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["list-skills", "--json"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "reference-contract-repair" in output
