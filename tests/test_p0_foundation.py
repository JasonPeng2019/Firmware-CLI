from __future__ import annotations

import argparse
import io

import pytest

from pyocd_debug_mcp.brain import cli as brain_cli
from pyocd_debug_mcp.brain.action_policy import classify_action
from pyocd_debug_mcp.brain.actions import FinalizeAction, TurnDecision, WaitAction
from pyocd_debug_mcp.brain.client_actions import (
    ClientActionLoadError,
    ClientActionRecord,
    GatedClientActionServer,
    InMemoryClientActionStore,
    load_client_actions_from_specs,
    parse_client_action_spec,
    render_client_action_prompt_section,
    run_client_action,
)
from pyocd_debug_mcp.brain.config import BrainConfigError, build_turnkey_invocation
from pyocd_debug_mcp.brain.decision_types import (
    ActionBatch,
    ActionCall,
    BoardDecision,
    EarlyExitVerdict,
    IterationEstimate,
    TimeoutProposal,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderProgressUpdate,
    ProviderSessionState,
    ProviderTurn,
)
from pyocd_debug_mcp.timeouts import (
    TurnkeyTimeoutConfig,
    TurnkeyTimeoutUpdate,
    apply_turnkey_timeout_update,
)


def test_board_decision_validates_board_action_shape() -> None:
    decision = BoardDecision.model_validate(
        {
            "decision_kind": "board_action",
            "action_batch": {
                "calls": [
                    {
                        "action_type": "server_tool",
                        "arguments": {"tool_name": "connect"},
                    }
                ]
            },
            "timeout_proposal": {"connect_seconds": 20.0},
            "iteration_estimate": {"requested_max_iterations": 8},
        }
    )

    assert decision.action_batch == ActionBatch(
        calls=(ActionCall(action_type="server_tool", arguments={"tool_name": "connect"}),)
    )
    assert decision.timeout_proposal == TimeoutProposal(connect_seconds=20.0)
    assert decision.iteration_estimate == IterationEstimate(requested_max_iterations=8)


def test_board_decision_validates_return_shape() -> None:
    decision = BoardDecision(
        decision_kind="return",
        early_exit=EarlyExitVerdict(
            verdict="needs_intervention",
            reason="Operator must reconnect power before continuing.",
        ),
    )

    assert decision.action_batch is None
    assert decision.early_exit is not None


def test_turnkey_timeout_update_is_partial_and_deterministic() -> None:
    base = TurnkeyTimeoutConfig()
    updated = apply_turnkey_timeout_update(
        base,
        TurnkeyTimeoutUpdate(connect_seconds=75.0),
    )

    assert updated.connect_seconds == 75.0
    assert updated.flash_seconds == base.flash_seconds
    assert updated.tool_timeout_seconds("connect", serial_read_seconds=3.0) == 75.0
    assert updated.tool_timeout_seconds("read_serial", serial_read_seconds=3.0) == 30.0


def test_provider_turn_carries_optional_session_and_progress_fields() -> None:
    turn = ProviderTurn(
        decision=TurnDecision(
            observation_summary="Connected cleanly.",
            classification="healthy",
            action=FinalizeAction(
                final_status="diagnosed_only",
                classification="healthy",
                root_cause="No fault found.",
                summary="Healthy board.",
            ),
        ),
        output_text="{}",
        response_id="resp-1",
        session_state=ProviderSessionState(provider_session_id="sess-1", response_id="resp-1", turn_index=3),
        progress_updates=(ProviderProgressUpdate(stage="thinking", message="provider is reasoning"),),
    )

    assert turn.session_state is not None
    assert turn.session_state.turn_index == 3
    assert turn.progress_updates[0].stage == "thinking"


def test_client_action_store_lists_records_sorted_by_name() -> None:
    store = InMemoryClientActionStore(
        [
            ClientActionRecord(name="z-last", relative_path="client_actions/z.py"),
            ClientActionRecord(name="a-first", relative_path="client_actions/a.py"),
        ]
    )

    assert [record.name for record in store.list_actions()] == ["a-first", "z-last"]
    assert store.get_action("a-first") is not None


def test_client_action_specs_load_validated_session_scripts(tmp_path) -> None:
    script = tmp_path / "uart_write.py"
    script.write_text(
        '"""Write a UART command through the gated server API."""\n\n'
        "async def run(inputs, server):\n"
        "    return await server.call_tool('write_serial', {'text': inputs['text']})\n",
        encoding="utf-8",
    )

    assert parse_client_action_spec(f"uart_write={script}") == ("uart_write", str(script))

    store = load_client_actions_from_specs((f"uart_write={script}",))
    record = store.get_action("uart_write")
    assert record is not None
    assert record.description == "Write a UART command through the gated server API."

    prompt_section = render_client_action_prompt_section(store)
    assert "name=uart_write" in prompt_section
    assert "sha256=" in prompt_section


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("missing_separator", "NAME=PATH"),
        ("bad name=script.py", "letters, digits"),
        ("name=", "path cannot be empty"),
    ],
)
def test_client_action_specs_reject_bad_cli_shapes(spec: str, message: str) -> None:
    with pytest.raises(ClientActionLoadError, match=message):
        parse_client_action_spec(spec)


def test_client_action_loader_rejects_duplicate_missing_or_invalid_scripts(tmp_path) -> None:
    script = tmp_path / "no_run.py"
    script.write_text("VALUE = 1\n", encoding="utf-8")
    valid_script = tmp_path / "valid.py"
    valid_script.write_text(
        "async def run(inputs, server):\n"
        "    return inputs\n",
        encoding="utf-8",
    )

    with pytest.raises(ClientActionLoadError, match="duplicate"):
        load_client_actions_from_specs((f"uart={valid_script}", f"uart={valid_script}"))

    with pytest.raises(ClientActionLoadError, match="does not exist"):
        load_client_actions_from_specs(("uart=missing.py",), base_dir=tmp_path)

    with pytest.raises(ClientActionLoadError, match="must define run"):
        load_client_actions_from_specs((f"uart={script}",))


def test_action_policy_classifies_branch_b_boundaries() -> None:
    assert classify_action("read_file") == "model_native_host"
    assert classify_action("wait") == "brain_local"
    assert classify_action("run_script") == "client_action"
    assert classify_action("write_serial") == "server_native"


def test_turn_decision_accepts_action_batch_and_wait_action() -> None:
    decision = TurnDecision.model_validate(
        {
            "observation_summary": "Need the board to settle before UART read.",
            "classification": None,
            "action_batch": {
                "calls": [
                    {"action_type": "wait", "arguments": {"seconds": 0.1}},
                    {"action_type": "read_serial", "arguments": {"read_seconds": 1.0}},
                ]
            },
        }
    )

    assert decision.action is None
    assert decision.action_batch is not None
    assert decision.action_batch.calls[0].action_type == "wait"
    assert WaitAction(seconds=0.1).seconds == 0.1


@pytest.mark.anyio
async def test_client_action_snapshot_hash_and_gated_server_api() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_call(tool_name: str, arguments: dict[str, object]) -> str:
        calls.append((tool_name, arguments))
        return "ok"

    store = InMemoryClientActionStore(
        [
            ClientActionRecord(
                name="ping-uart",
                relative_path="client_actions/ping_uart.py",
                content=(
                    "async def run(inputs, server):\n"
                    "    result = await server.call_tool('write_serial', {'text': inputs['text']})\n"
                    "    return {'tool_result': result}\n"
                ),
            )
        ]
    )
    snapshot = store.snapshot_action("ping-uart")
    assert snapshot is not None
    assert len(snapshot.content_sha256) == 64

    server = GatedClientActionServer(fake_call, allowed_tools={"write_serial"})
    result = await run_client_action(snapshot, inputs={"text": "hello"}, server=server)

    assert result == {"tool_result": "ok"}
    assert calls == [("write_serial", {"text": "hello"})]


@pytest.mark.anyio
async def test_client_action_gated_server_api_rejects_unapproved_tool() -> None:
    async def fake_call(tool_name: str, arguments: dict[str, object]) -> str:
        raise AssertionError("unapproved tool should not run")

    store = InMemoryClientActionStore(
        [
            ClientActionRecord(
                name="bad",
                relative_path="client_actions/bad.py",
                content=(
                    "async def run(inputs, server):\n"
                    "    return await server.call_tool('raw_shell', {})\n"
                ),
            )
        ]
    )
    snapshot = store.snapshot_action("bad")
    assert snapshot is not None

    server = GatedClientActionServer(fake_call, allowed_tools={"write_serial"})
    with pytest.raises(PermissionError, match="raw_shell"):
        await run_client_action(snapshot, inputs={}, server=server)


def test_turnkey_invocation_carries_p0_hook_fields_by_default() -> None:
    invocation = build_turnkey_invocation(
        mode="freeform",
        provider="codex-cli",
        board_id="nucleo_l476rg",
        task="Verify the board.",
        model=None,
        max_iters=4,
        serial_read_seconds=1.0,
    )

    assert invocation.timeout_config.default_tool_seconds == 30.0
    assert invocation.timeout_proposal is None
    assert invocation.iteration_estimate is None


def test_brain_cli_parser_accepts_planning_hook_arguments() -> None:
    parser = brain_cli.build_parser()

    args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nrf52833dk",
            "--task",
            "Verify this board.",
            "--timeout-config-json",
            "{\"connect_seconds\": 42.0}",
            "--timeout-proposal-json",
            "{\"provider_seconds\": 120.0}",
            "--iteration-estimate-json",
            "{\"requested_max_iterations\": 7}",
            "--client-action",
            "uart_write=client_actions/uart_write.py",
        ]
    )

    assert args.timeout_config_json == "{\"connect_seconds\": 42.0}"
    assert args.timeout_proposal_json == "{\"provider_seconds\": 120.0}"
    assert args.iteration_estimate_json == "{\"requested_max_iterations\": 7}"
    assert args.client_action == ["uart_write=client_actions/uart_write.py"]


def test_brain_cli_parser_accepts_task_file_and_task_stdin_sources(tmp_path) -> None:
    parser = brain_cli.build_parser()
    task_file = tmp_path / "task.txt"
    task_file.write_text(
        'Use action_batch with {"action_type":"run_script"} and preserve these quotes.\n',
        encoding="utf-8",
    )

    file_args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nucleo_l476rg",
            "--task-file",
            str(task_file),
        ]
    )
    stdin_args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nucleo_l476rg",
            "--task-stdin",
        ]
    )

    assert brain_cli.resolve_task_input(file_args) == task_file.read_text(encoding="utf-8")
    assert (
        brain_cli.resolve_task_input(stdin_args, stdin=io.StringIO("Verify from stdin.\n"))
        == "Verify from stdin.\n"
    )


def test_brain_cli_task_sources_are_mutually_exclusive_and_non_empty(tmp_path) -> None:
    parser = brain_cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--board-id",
                "nucleo_l476rg",
                "--task",
                "inline",
                "--task-stdin",
            ]
        )

    empty_file = tmp_path / "empty.txt"
    empty_file.write_text(" \n", encoding="utf-8")
    args = parser.parse_args(
        [
            "run",
            "--board-id",
            "nucleo_l476rg",
            "--task-file",
            str(empty_file),
        ]
    )
    with pytest.raises(BrainConfigError, match="empty task text"):
        brain_cli.resolve_task_input(args)


def test_brain_cli_timeout_config_json_applies_partial_override() -> None:
    config = brain_cli._parse_timeout_config_json("{\"connect_seconds\": 42.0}")

    assert config is not None
    assert config.connect_seconds == 42.0
    assert config.flash_seconds == TurnkeyTimeoutConfig().flash_seconds


def test_brain_cli_rejects_unknown_timeout_override_keys() -> None:
    with pytest.raises(Exception, match="unsupported keys"):
        brain_cli._parse_timeout_config_json("{\"not_real\": 1}")


@pytest.mark.anyio
async def test_brain_cli_run_freeform_threads_planning_hooks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def _fake_run_freeform_task(**kwargs: object) -> object:
        captured.update(kwargs)
        return argparse.Namespace(
            result=argparse.Namespace(
                final_status="healthy_confirmed",
                board_id="nrf52833dk",
                session_id="sess-1",
                classification="healthy",
                summary="Healthy.",
                root_cause="None.",
                verification=argparse.Namespace(
                    flash_ok=True,
                    uart_ok=True,
                    symbol_ok=True,
                    green_check_ok=True,
                ),
            ),
            run_root=None,
        )

    monkeypatch.setattr(brain_cli, "run_freeform_task", _fake_run_freeform_task)
    args = argparse.Namespace(
        board_id="nrf52833dk",
        task="Verify this board.",
        provider="codex-cli",
        model=None,
        max_iters=4,
        serial_read_seconds=1.0,
        port=None,
        flash_artifact=None,
        elf=None,
        workspace_root=None,
        build_command=None,
        client_action=[],
        task_file=None,
        task_stdin=False,
        timeout_config_json="{\"connect_seconds\": 42.0, \"provider_seconds\": 111.0}",
        timeout_proposal_json="{\"provider_seconds\": 120.0}",
        iteration_estimate_json="{\"requested_max_iterations\": 7}",
    )

    await brain_cli._run_freeform(args)

    timeout_config = captured["timeout_config"]
    assert isinstance(timeout_config, TurnkeyTimeoutConfig)
    assert timeout_config.connect_seconds == 42.0
    assert timeout_config.provider_seconds == 111.0
    assert captured["timeout_proposal"] == TimeoutProposal(provider_seconds=120.0)
    assert captured["iteration_estimate"] == IterationEstimate(requested_max_iterations=7)
    assert captured["client_action_specs"] == ()


@pytest.mark.anyio
async def test_brain_cli_run_freeform_threads_task_file_text(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    task_file = tmp_path / "task.txt"
    task_text = 'Fix using {"kind":"run_script"} without shell quoting issues.\n'
    task_file.write_text(task_text, encoding="utf-8")
    captured: dict[str, object] = {}

    async def _fake_run_freeform_task(**kwargs: object) -> object:
        captured.update(kwargs)
        return argparse.Namespace(
            result=argparse.Namespace(
                final_status="diagnosed_only",
                board_id="nucleo_l476rg",
                session_id="sess-1",
                classification="healthy",
                summary="Done.",
                root_cause="None.",
                verification=argparse.Namespace(
                    flash_ok=False,
                    uart_ok=False,
                    symbol_ok=False,
                    green_check_ok=False,
                ),
            ),
            run_root=None,
        )

    monkeypatch.setattr(brain_cli, "run_freeform_task", _fake_run_freeform_task)
    args = argparse.Namespace(
        board_id="nucleo_l476rg",
        task=None,
        task_file=str(task_file),
        task_stdin=False,
        provider="codex-cli",
        model=None,
        max_iters=4,
        serial_read_seconds=1.0,
        port=None,
        flash_artifact=None,
        elf=None,
        workspace_root=None,
        build_command=None,
        client_action=[],
        timeout_config_json=None,
        timeout_proposal_json=None,
        iteration_estimate_json=None,
    )

    await brain_cli._run_freeform(args)

    assert captured["task"] == task_text
