from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from pyocd_debug_mcp.brain.events import BrainEvent
from pyocd_debug_mcp.ux import cli as ux_cli
from pyocd_debug_mcp.ux import shell as ux_shell
from pyocd_debug_mcp.ux.artifacts import artifact_entries
from pyocd_debug_mcp.ux.commands import SlashCommand, TaskInput, parse_shell_input
from pyocd_debug_mcp.ux.history import HistoryListing, UXHistoryError, load_session_bundle, list_history
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
        arg_text="nrf52833dk",
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

    listing = list_history(runs_root=tmp_path, limit=None)

    assert [entry.session_id for entry in listing.entries] == [
        "20260623T010000Z-bbbb2222",
        "20260623T000000Z-aaaa1111",
    ]
    assert listing.entries[0].board_id == "nrf52833dk"
    assert listing.entries[0].provider == "claude-cli"
    assert listing.warnings == ()


def test_list_history_skips_malformed_runs_and_collects_warnings(tmp_path: Path) -> None:
    _seed_run(
        tmp_path,
        "20260623T000000Z-valid111",
        board_id="nucleo_l476rg",
        provider="codex-cli",
        task="Healthy run",
    )
    bad_run = tmp_path / "20260623T020000Z-badjson"
    bad_run.mkdir(parents=True)
    (bad_run / "run-metadata").mkdir(parents=True)
    (bad_run / "run-metadata" / "turnkey_request.json").write_text("{not json}\n", encoding="utf-8")

    listing = list_history(runs_root=tmp_path, limit=None)

    assert [entry.session_id for entry in listing.entries] == ["20260623T000000Z-valid111"]
    assert len(listing.warnings) == 1
    assert listing.warnings[0].session_id == "20260623T020000Z-badjson"
    assert "Expecting property name enclosed in double quotes" in listing.warnings[0].message


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


def test_load_session_bundle_raises_on_malformed_selected_run(tmp_path: Path) -> None:
    bad_run = tmp_path / "20260623T070000Z-badselected"
    (bad_run / "run-metadata").mkdir(parents=True)
    (bad_run / "run-metadata" / "turnkey_request.json").write_text("{bad json}\n", encoding="utf-8")

    with pytest.raises(UXHistoryError, match="Expecting property name enclosed in double quotes"):
        load_session_bundle("20260623T070000Z-badselected", runs_root=tmp_path)


def test_renderer_renders_history_table() -> None:
    stream = io.StringIO()
    renderer = UXRenderer(console=Console(file=stream, force_terminal=False, color_system=None))
    renderer.render_history(
        HistoryListing(
            entries=(
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
                )(),
            ),
            warnings=(),
        )
    )
    output = stream.getvalue()
    assert "Recent Sessions" in output
    assert "nrf52833dk" in output


def test_renderer_non_tty_fallback_prints_status_lines() -> None:
    stream = io.StringIO()
    renderer = UXRenderer(console=Console(file=stream, force_terminal=False, color_system=None))
    renderer.emit(
        BrainEvent(
            event_kind="provider_turn_start",
            timestamp="2026-06-23T00:00:00Z",
            board_id="nrf52833dk",
            iteration=1,
            session_id="20260623T000000Z-aaaa1111",
            provider="codex-cli",
            model=None,
            message="provider is thinking",
            details={},
        )
    )
    assert "provider is thinking" in stream.getvalue()


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


def _make_renderer(stream: io.StringIO | None = None) -> UXRenderer:
    return UXRenderer(raw_output="off", console=Console(file=stream or io.StringIO(), force_terminal=False, color_system=None))


def _make_shell(renderer: UXRenderer | None = None) -> ux_shell.OperatorShell:
    return ux_shell.OperatorShell(renderer=renderer or _make_renderer())


def test_operator_shell_defaults_to_summary_first_raw_mode() -> None:
    shell = _make_shell()
    assert shell.renderer.raw_output == "off"
    assert shell.context.raw_output == "off"


def test_operator_shell_falls_back_to_dummy_output_without_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoConsoleError(RuntimeError):
        pass

    calls: list[dict[str, object]] = []

    def fake_prompt_session(*args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        if "output" not in kwargs:
            raise NoConsoleError("no console")
        return SimpleNamespace(prompt=lambda *p_args, **p_kwargs: "/quit")

    monkeypatch.setattr(ux_shell, "_NO_CONSOLE_ERRORS", (NoConsoleError,))
    monkeypatch.setattr(ux_shell, "PromptSession", fake_prompt_session)

    shell = _make_shell()

    assert len(calls) == 2
    assert calls[0] == {}
    assert isinstance(calls[1]["output"], ux_shell.DummyOutput)
    assert shell._session is not None


def test_parse_shell_input_preserves_raw_arg_text_for_build_command() -> None:
    parsed = parse_shell_input('/build-command "west build -b nucleo_l476rg"')
    assert parsed == SlashCommand(
        name="build-command",
        args=("west build -b nucleo_l476rg",),
        arg_text='"west build -b nucleo_l476rg"',
    )


def test_shell_workspace_and_build_context_commands_persist_state(tmp_path: Path) -> None:
    stream = io.StringIO()
    shell = _make_shell(_make_renderer(stream))
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    flash_artifact = tmp_path / "firmware.elf"
    flash_artifact.write_text("elf", encoding="utf-8")
    symbol_artifact = tmp_path / "firmware.sym.elf"
    symbol_artifact.write_text("sym", encoding="utf-8")

    assert shell._dispatch_command(parse_shell_input(f"/workspace {workspace_root}")) is True
    assert shell.context.workspace_root == str(workspace_root.resolve())

    assert shell._dispatch_command(parse_shell_input('/build-command "west build -b nucleo_l476rg"')) is True
    assert shell.context.build_command == "west build -b nucleo_l476rg"

    assert shell._dispatch_command(parse_shell_input(f"/flash-artifact {flash_artifact}")) is True
    assert shell.context.flash_artifact == str(flash_artifact.resolve())

    assert shell._dispatch_command(parse_shell_input(f"/elf {symbol_artifact}")) is True
    assert shell.context.symbol_artifact == str(symbol_artifact.resolve())

    assert shell._dispatch_command(parse_shell_input("/workspace clear")) is True
    assert shell.context.workspace_root is None

    assert shell._dispatch_command(parse_shell_input("/build-command clear")) is True
    assert shell.context.build_command is None

    assert shell._dispatch_command(parse_shell_input("/flash-artifact default")) is True
    assert shell.context.flash_artifact is None

    assert shell._dispatch_command(parse_shell_input("/elf default")) is True
    assert shell.context.symbol_artifact is None


def test_shell_raw_command_toggles_modes_and_supports_last() -> None:
    shell = _make_shell()
    shown = {"called": False}
    shell.renderer.show_last_raw = lambda: shown.update(called=True)  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_shell_input("/raw on")) is True
    assert shell.renderer.raw_output == "all"

    assert shell._dispatch_command(parse_shell_input("/raw off")) is True
    assert shell.renderer.raw_output == "off"

    assert shell._dispatch_command(parse_shell_input("/raw last")) is True
    assert shown["called"] is True


def test_guided_verify_ignores_workspace_context_but_keeps_artifact_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    shell = _make_shell()
    shell.context.board_id = "nrf52833dk"
    shell.context.workspace_root = str((tmp_path / "workspace").resolve())
    shell.context.build_command = "west build -b nrf52833dk"
    shell.context.flash_artifact = str((tmp_path / "firmware.elf").resolve())
    shell.context.symbol_artifact = str((tmp_path / "firmware.sym.elf").resolve())

    captured: dict[str, object] = {}

    async def _fake_run_freeform_task(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            result=SimpleNamespace(
                session_id="20260623T040000Z-guided",
                board_id="nrf52833dk",
                classification="healthy",
                final_status="healthy_confirmed",
                summary="Healthy.",
                root_cause="Healthy baseline.",
                verification=SimpleNamespace(
                    flash_ok=True,
                    uart_ok=True,
                    symbol_ok=True,
                    green_check_ok=True,
                ),
            )
        )

    monkeypatch.setattr(ux_shell, "run_freeform_task", _fake_run_freeform_task)
    shell.renderer.render_execution = lambda execution: None  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_shell_input("/verify focus on UART evidence")) is True
    assert captured["workspace_root"] is None
    assert captured["build_command"] is None
    assert captured["flash_artifact"] == shell.context.flash_artifact
    assert captured["elf"] == shell.context.symbol_artifact
    assert "focus on UART evidence" in str(captured["task"])
    assert "Do not edit source files" in str(captured["task"])


def test_guided_repair_refuses_without_required_context() -> None:
    stream = io.StringIO()
    shell = _make_shell(_make_renderer(stream))
    shell.context.board_id = "nucleo_l476rg"

    assert shell._dispatch_command(parse_shell_input("/repair restore the healthy image")) is True
    output = stream.getvalue()
    assert "ux/missing-repair-context" in output
    assert "/workspace <path>" in output


def test_guided_repair_uses_workspace_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shell = _make_shell()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    shell.context.board_id = "nucleo_l476rg"
    shell.context.workspace_root = str(workspace_root.resolve())
    shell.context.build_command = "west build -b nucleo_l476rg"

    captured: dict[str, object] = {}

    async def _fake_run_freeform_task(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            result=SimpleNamespace(
                session_id="20260623T050000Z-repair",
                board_id="nucleo_l476rg",
                classification="code_bug",
                final_status="fixed",
                summary="Fixed.",
                root_cause="Wrong application output.",
                verification=SimpleNamespace(
                    flash_ok=True,
                    uart_ok=True,
                    symbol_ok=True,
                    green_check_ok=True,
                ),
            )
        )

    monkeypatch.setattr(ux_shell, "run_freeform_task", _fake_run_freeform_task)
    shell.renderer.render_execution = lambda execution: None  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_shell_input("/repair restore boot ok output")) is True
    assert captured["workspace_root"] == str(workspace_root.resolve())
    assert captured["build_command"] == "west build -b nucleo_l476rg"
    assert "restore boot ok output" in str(captured["task"])


def test_artifact_shortcuts_resolve_current_or_latest_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_root = _seed_run(
        tmp_path,
        "20260623T060000Z-shortcuts",
        board_id="nrf52833dk",
        provider="codex-cli",
        task="Show prompt shortcut",
    )
    (run_root / "logs" / "brain_events.jsonl").write_text("{\"event_kind\": \"run_start\"}\n", encoding="utf-8")
    (run_root / "logs" / "events.jsonl").write_text("{\"tool_name\": \"connect\"}\n", encoding="utf-8")
    bundle = load_session_bundle("20260623T060000Z-shortcuts", runs_root=tmp_path)

    shell = _make_shell()
    rendered: list[str] = []
    monkeypatch.setattr(ux_shell, "load_session_bundle", lambda session_id: bundle)
    monkeypatch.setattr(
        ux_shell,
        "list_history",
        lambda limit=1: HistoryListing(
            entries=(type("Entry", (), {"session_id": "20260623T060000Z-shortcuts"})(),),
            warnings=(),
        ),
    )
    shell.renderer.render_artifact_entry = lambda entry, title=None: rendered.append(title or entry.label)  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_shell_input("/prompt")) is True
    assert rendered == ["prompt: prompt"]

    rendered.clear()
    assert shell._dispatch_command(parse_shell_input("/events")) is True
    assert rendered == ["events: brain_events", "events: server_events"]


def test_shell_fallback_session_selection_skips_malformed_newest_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valid_run = _seed_run(
        tmp_path,
        "20260623T060000Z-valid",
        board_id="nrf52833dk",
        provider="codex-cli",
        task="Healthy run",
    )
    bad_run = tmp_path / "20260623T070000Z-bad"
    (bad_run / "run-metadata").mkdir(parents=True)
    (bad_run / "run-metadata" / "turnkey_request.json").write_text("{bad json}\n", encoding="utf-8")

    shell = _make_shell()
    bundle = load_session_bundle("20260623T060000Z-valid", runs_root=tmp_path)

    monkeypatch.setattr(
        ux_shell,
        "list_history",
        lambda limit=1: list_history(runs_root=tmp_path, limit=limit),
    )
    monkeypatch.setattr(
        ux_shell,
        "load_session_bundle",
        lambda session_id: load_session_bundle(session_id, runs_root=tmp_path),
    )
    selected = shell._load_selected_bundle(None)

    assert selected == bundle
    assert valid_run.name == "20260623T060000Z-valid"
