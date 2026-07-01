from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from rich.console import Console

from pyocd_debug_mcp.brain.events import BrainEvent
from pyocd_debug_mcp.brain.provider_types import ProviderResumeFailure, ProviderResumeFailureRecord
from pyocd_debug_mcp.ux import cli as ux_cli
from pyocd_debug_mcp.ux import shell as ux_shell
from pyocd_debug_mcp.ux.artifacts import artifact_entries
from pyocd_debug_mcp.ux.commands import SlashCommand, TaskInput, parse_shell_input
from pyocd_debug_mcp.ux.history import (
    HistoryEntry,
    HistoryListing,
    UXHistoryError,
    load_session_bundle,
    list_history,
)
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


def parse_slash_command(text: str) -> SlashCommand:
    parsed = parse_shell_input(text)
    assert isinstance(parsed, SlashCommand)
    return parsed


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
                HistoryEntry(
                    session_id="20260623T030000Z-dddd4444",
                    run_root=Path("."),
                    board_id="nrf52833dk",
                    provider="codex-cli",
                    model=None,
                    run_mode="freeform",
                    final_status="healthy_confirmed",
                    case_id=None,
                    task_summary="Verify this reference firmware is healthy.",
                    created_at=None,
                ),
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


def test_renderer_prints_provider_progress_events() -> None:
    stream = io.StringIO()
    renderer = UXRenderer(console=Console(file=stream, force_terminal=False, color_system=None))
    renderer.emit(
        BrainEvent(
            event_kind="provider_progress",
            timestamp="2026-06-25T00:00:00Z",
            board_id="nrf52833dk",
            iteration=1,
            session_id="20260625T000000Z-aaaa1111",
            provider="openai-api",
            model="gpt-test",
            message="Using OpenAI native continuation with the prior response id.",
            details={"stage": "continuation"},
        )
    )

    output = stream.getvalue()
    assert "provider" in output
    assert "continuation" in output
    assert "prior response id" in output


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


def test_operator_cli_parser_supports_task_file_source(tmp_path: Path) -> None:
    parser = ux_cli.build_parser()
    task_file = tmp_path / "task.txt"
    task_file.write_text('Use {"action_type":"run_script"}.\n', encoding="utf-8")

    args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nucleo_l476rg",
            "--task-file",
            str(task_file),
        ]
    )

    assert ux_cli.resolve_task_input(args) == task_file.read_text(encoding="utf-8")


def test_operator_cli_render_run_uses_task_file_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    task_file = tmp_path / "task.txt"
    task_file.write_text("Diagnose from a task file.\n", encoding="utf-8")
    captured: dict[str, object] = {}

    async def _fake_run_freeform_task(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(
            result=SimpleNamespace(
                session_id="20260628T000000Z-taskfile",
                board_id="nucleo_l476rg",
                classification="healthy",
                final_status="diagnosed_only",
                summary="Done.",
                root_cause="None.",
                verification=SimpleNamespace(
                    flash_ok=False,
                    uart_ok=False,
                    symbol_ok=False,
                    green_check_ok=False,
                ),
            ),
            run_root=None,
        )

    monkeypatch.setattr(ux_cli, "run_freeform_task", _fake_run_freeform_task)
    monkeypatch.setattr(ux_cli.UXRenderer, "render_execution", lambda self, execution: None)
    args = ux_cli.build_parser().parse_args(
        [
            "run",
            "--board-id",
            "nucleo_l476rg",
            "--task-file",
            str(task_file),
        ]
    )

    assert ux_cli._render_run(args) == 0
    assert captured["task"] == "Diagnose from a task file.\n"


def test_operator_cli_parser_supports_memory_controls() -> None:
    parser = ux_cli.build_parser()

    args = parser.parse_args(
        [
            "benchmark",
            "--case-id",
            "nrf52833dk__k001_reference_green",
            "--memory-mode",
            "model-summary",
            "--native-sync-every",
            "6",
            "--recent-turn-detail-limit",
            "2",
            "--memory-summary-max-chars",
            "1800",
            "--no-preload-common-details",
        ]
    )

    assert args.memory_mode == "model-summary"
    assert args.native_sync_every == 6
    assert args.recent_turn_detail_limit == 2
    assert args.memory_summary_max_chars == 1800
    assert args.preload_common_details is False


def _make_renderer(stream: io.StringIO | None = None) -> UXRenderer:
    return UXRenderer(
        raw_output="off",
        console=Console(file=stream or io.StringIO(), force_terminal=False, color_system=None),
    )


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


def test_operator_shell_falls_back_when_patch_stdout_has_no_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class NoConsoleError(RuntimeError):
        pass

    class BrokenPatchStdout:
        def __enter__(self) -> object:
            raise NoConsoleError("no console")

        def __exit__(self, *args: object) -> bool:
            return False

    prompts = iter(["/quit"])
    calls: list[dict[str, object]] = []

    def fake_prompt_session(*args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        return SimpleNamespace(prompt=lambda *p_args, **p_kwargs: next(prompts))

    monkeypatch.setattr(ux_shell.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(ux_shell, "_NO_CONSOLE_ERRORS", (NoConsoleError,))
    monkeypatch.setattr(ux_shell, "patch_stdout", lambda: BrokenPatchStdout())
    monkeypatch.setattr(ux_shell, "PromptSession", fake_prompt_session)

    shell = _make_shell()

    assert shell.run() == 0
    assert calls[0] == {}
    assert isinstance(calls[1]["output"], ux_shell.DummyOutput)


def test_operator_shell_reads_piped_commands_without_prompt_toolkit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = io.StringIO()

    def fail_patch_stdout() -> object:
        raise AssertionError("pipe mode should not call prompt_toolkit patch_stdout")

    monkeypatch.setattr(ux_shell.sys, "stdin", io.StringIO("/help\n/quit\n"))
    monkeypatch.setattr(ux_shell, "patch_stdout", fail_patch_stdout)

    shell = _make_shell(_make_renderer(stream))

    assert shell.run() == 0
    assert "Slash commands" in stream.getvalue()


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

    assert shell._dispatch_command(parse_slash_command(f"/workspace {workspace_root}")) is True
    assert shell.context.workspace_root == str(workspace_root.resolve())

    assert (
        shell._dispatch_command(parse_slash_command('/build-command "west build -b nucleo_l476rg"'))
        is True
    )
    assert shell.context.build_command == "west build -b nucleo_l476rg"

    assert shell._dispatch_command(parse_slash_command(f"/flash-artifact {flash_artifact}")) is True
    assert shell.context.flash_artifact == str(flash_artifact.resolve())

    assert shell._dispatch_command(parse_slash_command(f"/elf {symbol_artifact}")) is True
    assert shell.context.symbol_artifact == str(symbol_artifact.resolve())

    assert shell._dispatch_command(parse_slash_command("/workspace clear")) is True
    assert shell.context.workspace_root is None

    assert shell._dispatch_command(parse_slash_command("/build-command clear")) is True
    assert shell.context.build_command is None

    assert shell._dispatch_command(parse_slash_command("/flash-artifact default")) is True
    assert shell.context.flash_artifact is None

    assert shell._dispatch_command(parse_slash_command("/elf default")) is True
    assert shell.context.symbol_artifact is None


def test_shell_raw_command_toggles_modes_and_supports_last() -> None:
    shell = _make_shell()
    shown = {"called": False}
    shell.renderer.show_last_raw = lambda: shown.update(called=True)  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_slash_command("/raw on")) is True
    assert shell.renderer.raw_output == "all"

    assert shell._dispatch_command(parse_slash_command("/raw off")) is True
    assert shell.renderer.raw_output == "off"

    assert shell._dispatch_command(parse_slash_command("/raw last")) is True
    assert shown["called"] is True


def test_shell_memory_commands_update_context_and_reject_invalid_values() -> None:
    stream = io.StringIO()
    shell = _make_shell(_make_renderer(stream))

    assert shell._dispatch_command(parse_slash_command("/memory-mode model-summary")) is True
    assert shell.context.memory_mode == "model-summary"

    assert shell._dispatch_command(parse_slash_command("/native-sync-every 0")) is True
    assert shell.context.native_sync_every == 0

    assert shell._dispatch_command(parse_slash_command("/native-sync-every -1")) is True
    assert "ux/invalid-native-sync" in stream.getvalue()


def test_shell_provider_resume_prompt_maps_retry_new_and_abort_choices() -> None:
    stream = io.StringIO()
    shell = _make_shell(_make_renderer(stream))
    failure = ProviderResumeFailure(
        ProviderResumeFailureRecord(
            provider="codex-cli",
            remote_strategy="codex-thread-resume",
            continuation_mode="remote-primary",
            continuation_path="remote-resume",
            remote_handle_kind="thread_id",
            expected_handle_id="thread-parent",
            turn_index=3,
            failure_text="resume failed",
            local_memory_available=True,
        )
    )

    for typed, expected in (
        ("r", "retry"),
        ("n", "new-session-from-memory"),
        ("a", "abort"),
    ):
        shell._session = cast(
            Any, SimpleNamespace(prompt=lambda *_args, _typed=typed, **_kwargs: _typed)
        )

        assert shell._prompt_provider_resume_recovery(failure) == expected

    output = stream.getvalue()
    assert "Provider session resume failed" in output
    assert "Expected thread_id: thread-parent" in output
    assert "No new provider session has been started" in output


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

    assert shell._dispatch_command(parse_slash_command("/verify focus on UART evidence")) is True
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

    assert shell._dispatch_command(parse_slash_command("/repair restore the healthy image")) is True
    output = stream.getvalue()
    assert "ux/missing-repair-context" in output
    assert "/workspace <path>" in output


def test_guided_repair_uses_workspace_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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

    assert shell._dispatch_command(parse_slash_command("/repair restore boot ok output")) is True
    assert captured["workspace_root"] == str(workspace_root.resolve())
    assert captured["build_command"] == "west build -b nucleo_l476rg"
    assert "restore boot ok output" in str(captured["task"])


def test_artifact_shortcuts_resolve_current_or_latest_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_root = _seed_run(
        tmp_path,
        "20260623T060000Z-shortcuts",
        board_id="nrf52833dk",
        provider="codex-cli",
        task="Show prompt shortcut",
    )
    (run_root / "logs" / "brain_events.jsonl").write_text(
        '{"event_kind": "run_start"}\n', encoding="utf-8"
    )
    (run_root / "logs" / "events.jsonl").write_text('{"tool_name": "connect"}\n', encoding="utf-8")
    bundle = load_session_bundle("20260623T060000Z-shortcuts", runs_root=tmp_path)

    shell = _make_shell()
    rendered: list[str] = []
    monkeypatch.setattr(ux_shell, "load_session_bundle", lambda session_id: bundle)
    monkeypatch.setattr(
        ux_shell,
        "list_history",
        lambda limit=1: HistoryListing(
            entries=(
                HistoryEntry(
                    session_id="20260623T060000Z-shortcuts",
                    run_root=run_root,
                    board_id="nrf52833dk",
                    provider="codex-cli",
                    model=None,
                    run_mode="freeform",
                    final_status="healthy_confirmed",
                    case_id=None,
                    task_summary="Show prompt shortcut",
                    created_at=None,
                ),
            ),
            warnings=(),
        ),
    )
    shell.renderer.render_artifact_entry = lambda entry, title=None: rendered.append(
        title or entry.label
    )  # type: ignore[method-assign]

    assert shell._dispatch_command(parse_slash_command("/prompt")) is True
    assert rendered == ["prompt: prompt"]

    rendered.clear()
    assert shell._dispatch_command(parse_slash_command("/events")) is True
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
