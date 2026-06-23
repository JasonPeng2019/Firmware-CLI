from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from pyocd_debug_mcp.ux import cli as ux_cli
from pyocd_debug_mcp.ux.artifacts import artifact_entries
from pyocd_debug_mcp.ux.commands import SlashCommand, TaskInput, parse_shell_input
from pyocd_debug_mcp.ux.history import load_session_bundle, list_history
from pyocd_debug_mcp.ux.renderer import UXRenderer


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _seed_run(runs_root: Path, session_id: str, *, board_id: str, provider: str, task: str) -> Path:
    run_root = runs_root / session_id
    _write_json(
        run_root / "run-metadata" / "turnkey_request.json",
        {
            "board_id": board_id,
            "provider": provider,
            "model": None,
            "mode": "freeform",
            "task": task,
            "case_id": None,
        },
    )
    _write_json(
        run_root / "run-metadata" / "turnkey_result.json",
        {
            "board_id": board_id,
            "session_id": session_id,
            "final_status": "healthy_confirmed",
            "classification": "healthy",
            "summary": "Healthy baseline confirmed.",
        },
    )
    _write_json(
        run_root / "run-metadata" / "session.json",
        {
            "session_id": session_id,
            "board_id": board_id,
            "created_at": f"{session_id}-created",
        },
    )
    _write_json(run_root / "run-metadata" / "turnkey_state.json", {"iteration": 1})
    (run_root / "logs").mkdir(parents=True, exist_ok=True)
    (run_root / "logs" / "prompt.txt").write_text("prompt", encoding="utf-8")
    return run_root


def test_parse_shell_input_supports_plain_tasks_and_slash_commands() -> None:
    assert parse_shell_input("Verify this board.") == TaskInput(task="Verify this board.")
    assert parse_shell_input("/board nrf52833dk") == SlashCommand(
        name="board",
        args=("nrf52833dk",),
    )


def test_list_history_reads_saved_turnkey_runs_newest_first(tmp_path: Path) -> None:
    _seed_run(
        tmp_path,
        "20260623T000000Z-aaaa1111",
        board_id="nucleo_l476rg",
        provider="codex-cli",
        task="Older task",
    )
    _seed_run(
        tmp_path,
        "20260623T010000Z-bbbb2222",
        board_id="nrf52833dk",
        provider="claude-cli",
        task="Newer task",
    )

    entries = list_history(runs_root=tmp_path, limit=None)

    assert [entry.session_id for entry in entries] == [
        "20260623T010000Z-bbbb2222",
        "20260623T000000Z-aaaa1111",
    ]
    assert entries[0].board_id == "nrf52833dk"
    assert entries[0].provider == "claude-cli"


def test_load_session_bundle_and_artifact_entries(tmp_path: Path) -> None:
    run_root = _seed_run(
        tmp_path,
        "20260623T020000Z-cccc3333",
        board_id="nrf52833dk",
        provider="codex-cli",
        task="Show artifacts",
    )
    _write_json(run_root / "run-metadata" / "score.json", {"score": 100})

    bundle = load_session_bundle("20260623T020000Z-cccc3333", runs_root=tmp_path)
    labels = [entry.label for entry in artifact_entries(bundle)]

    assert bundle.request is not None
    assert bundle.result is not None
    assert "turnkey_request" in labels
    assert "turnkey_result" in labels
    assert "score" in labels


def test_renderer_renders_history_table() -> None:
    stream = io.StringIO()
    renderer = UXRenderer(console=Console(file=stream, force_terminal=False, color_system=None))
    renderer.render_history(
        [
            type(
                "Entry",
                (),
                {
                    "session_id": "20260623T030000Z-dddd4444",
                    "board_id": "nrf52833dk",
                    "provider": "codex-cli",
                    "run_mode": "freeform",
                    "final_status": "healthy_confirmed",
                    "task_summary": "Verify this reference firmware is healthy.",
                },
            )()
        ]
    )
    output = stream.getvalue()
    assert "Recent Sessions" in output
    assert "nrf52833dk" in output


def test_operator_cli_without_args_launches_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    launched: dict[str, bool] = {"called": False}

    class _FakeShell:
        def run(self) -> int:
            launched["called"] = True
            return 0

    monkeypatch.setattr(ux_cli, "OperatorShell", lambda: _FakeShell())

    assert ux_cli.main([]) == 0
    assert launched["called"] is True


def test_operator_cli_parser_supports_raw_output_flags() -> None:
    parser = ux_cli.build_parser()

    args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nrf52833dk",
            "--task",
            "Verify this board.",
            "--raw-output",
            "all",
        ]
    )

    assert args.command == "run"
    assert args.raw_output == "all"
