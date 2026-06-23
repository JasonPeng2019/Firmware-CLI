"""Interactive operator shell for the turnkey brain."""

from __future__ import annotations

from dataclasses import dataclass

import anyio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from pyocd_debug_mcp.brain.app import run_benchmark_case, run_benchmark_suite, run_freeform_task
from pyocd_debug_mcp.brain.config import BrainConfigError, TurnkeyProviderKind, cast_provider
from pyocd_debug_mcp.ux.commands import HELP_TEXT, ShellCommandError, SlashCommand, TaskInput, parse_shell_input
from pyocd_debug_mcp.ux.history import UXHistoryError, load_session_bundle, list_history
from pyocd_debug_mcp.ux.renderer import RawOutputPolicy, UXRenderer


@dataclass
class ShellContext:
    board_id: str | None = None
    provider: TurnkeyProviderKind | None = None
    model: str | None = None
    last_session_id: str | None = None
    raw_output: RawOutputPolicy = "final"

    def prompt_text(self) -> str:
        board = self.board_id or "board?"
        provider = self.provider or "provider:auto"
        model = self.model or "model:default"
        session = self.last_session_id or "session:-"
        return f"[{board}][{provider}][{model}][{session}] > "


class OperatorShell:
    def __init__(self, renderer: UXRenderer | None = None) -> None:
        self.renderer = renderer or UXRenderer(raw_output="all")
        self.context = ShellContext(raw_output=self.renderer.raw_output)
        self._session: PromptSession[str] = PromptSession()

    def run(self) -> int:
        self.renderer.print_info("pyocd-debug interactive shell. Use `/help` for commands.")
        with patch_stdout():
            while True:
                try:
                    text = self._session.prompt(self.context.prompt_text())
                except (EOFError, KeyboardInterrupt):
                    self.renderer.print_info("Exiting shell.")
                    return 0
                if not self._handle_input(text):
                    return 0

    def _handle_input(self, text: str) -> bool:
        try:
            parsed = parse_shell_input(text)
        except ShellCommandError as exc:
            self.renderer.print_error(str(exc))
            return True
        if parsed is None:
            return True
        if isinstance(parsed, TaskInput):
            return self._run_task(parsed.task)
        return self._dispatch_command(parsed)

    def _dispatch_command(self, command: SlashCommand) -> bool:
        if command.name == "help":
            self.renderer.print_info(HELP_TEXT)
            return True
        if command.name == "quit":
            return False
        if command.name == "board":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /board <id>")
                return True
            self.context.board_id = command.args[0]
            self.renderer.print_info(f"Board set to {self.context.board_id}.")
            return True
        if command.name == "provider":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /provider <name>")
                return True
            try:
                self.context.provider = cast_provider(command.args[0])
            except BrainConfigError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.renderer.print_info(f"Provider set to {self.context.provider}.")
            return True
        if command.name == "model":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /model <name|default>")
                return True
            self.context.model = None if command.args[0] == "default" else command.args[0]
            self.renderer.print_info(f"Model set to {self.context.model or 'default'}.")
            return True
        if command.name == "run":
            if not command.args:
                self.renderer.print_error("Usage: /run <task>")
                return True
            return self._run_task(" ".join(command.args))
        if command.name == "benchmark":
            if len(command.args) != 2 or command.args[0] not in {"case", "suite"}:
                self.renderer.print_error("Usage: /benchmark case <case_id> | /benchmark suite <suite_name>")
                return True
            if command.args[0] == "case":
                return self._run_benchmark_case(command.args[1])
            return self._run_benchmark_suite(command.args[1])
        if command.name == "history":
            self.renderer.render_history(list_history())
            return True
        if command.name == "show":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /show <session_id>")
                return True
            return self._show_session(command.args[0])
        if command.name == "rerun":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /rerun <session_id>")
                return True
            return self._rerun_session(command.args[0])
        if command.name == "artifacts":
            session_id = command.args[0] if command.args else self.context.last_session_id
            if session_id is None:
                self.renderer.print_error("No session selected. Use /artifacts <session_id> or run something first.")
                return True
            try:
                bundle = load_session_bundle(session_id)
            except UXHistoryError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.renderer.render_artifacts(bundle)
            return True
        if command.name == "raw":
            if len(command.args) != 1 or command.args[0] not in {"on", "off", "last"}:
                self.renderer.print_error("Usage: /raw on|off|last")
                return True
            if command.args[0] == "last":
                self.renderer.show_last_raw()
                return True
            self.renderer.raw_output = "all" if command.args[0] == "on" else "off"
            self.context.raw_output = self.renderer.raw_output
            self.renderer.print_info(f"Raw output mode set to {self.renderer.raw_output}.")
            return True
        self.renderer.print_error(f"Unknown command: /{command.name}")
        return True

    def _run_task(self, task: str) -> bool:
        if self.context.board_id is None:
            self.renderer.print_error("Select a board first with `/board <id>`.")
            return True
        try:
            execution = anyio.run(
                lambda: run_freeform_task(
                    board_id=self.context.board_id or "",
                    task=task,
                    provider=self.context.provider,
                    model=self.context.model,
                    event_sink=self.renderer.emit,
                )
            )
        except BrainConfigError as exc:
            self.renderer.print_error(str(exc))
            return True
        self.context.last_session_id = execution.result.session_id or self.renderer.current_session_id
        self.renderer.render_execution(execution)
        return True

    def _run_benchmark_case(self, case_id: str) -> bool:
        try:
            report = run_benchmark_case(
                case_id=case_id,
                provider=self.context.provider,
                model=self.context.model,
                event_sink=self.renderer.emit,
            )
        except BrainConfigError as exc:
            self.renderer.print_error(str(exc))
            return True
        self.context.last_session_id = report.session_id
        self.renderer.render_case_report(report)
        return True

    def _run_benchmark_suite(self, suite_name: str) -> bool:
        try:
            reports = run_benchmark_suite(
                suite_name=suite_name,
                provider=self.context.provider,
                model=self.context.model,
                event_sink=self.renderer.emit,
            )
        except BrainConfigError as exc:
            self.renderer.print_error(str(exc))
            return True
        if reports:
            self.context.last_session_id = reports[-1].session_id
        for report in reports:
            self.renderer.render_case_report(report)
        self.renderer.render_suite_summary(suite_name, reports)
        return True

    def _show_session(self, session_id: str) -> bool:
        try:
            bundle = load_session_bundle(session_id)
        except UXHistoryError as exc:
            self.renderer.print_error(str(exc))
            return True
        self.context.last_session_id = session_id
        self.renderer.render_session_bundle(bundle)
        return True

    def rerun_session(self, session_id: str) -> bool:
        return self._rerun_session(session_id)

    def _rerun_session(self, session_id: str) -> bool:
        try:
            bundle = load_session_bundle(session_id)
        except UXHistoryError as exc:
            self.renderer.print_error(str(exc))
            return True
        request = bundle.request
        if request is None:
            self.renderer.print_refusal(
                f"Refused [ux/missing-request]: session `{session_id}` has no turnkey_request.json."
            )
            return True
        mode = request.get("mode")
        provider = request.get("provider")
        model = request.get("model")
        if not isinstance(provider, str):
            self.renderer.print_refusal(
                f"Refused [ux/invalid-request]: session `{session_id}` has no valid provider."
            )
            return True
        try:
            request_provider = cast_provider(provider)
        except BrainConfigError as exc:
            self.renderer.print_refusal(f"Refused [ux/invalid-request]: {exc}")
            return True
        if mode == "freeform":
            task = request.get("task")
            board_id = request.get("board_id")
            if not isinstance(task, str) or not isinstance(board_id, str):
                self.renderer.print_refusal(
                    f"Refused [ux/invalid-request]: session `{session_id}` is missing freeform request fields."
                )
                return True
            try:
                execution = anyio.run(
                    lambda: run_freeform_task(
                        board_id=board_id,
                        task=task,
                        provider=request_provider,
                        model=model if isinstance(model, str) else None,
                        port=request.get("port_override") if isinstance(request.get("port_override"), str) else None,
                        flash_artifact=request.get("flash_artifact") if isinstance(request.get("flash_artifact"), str) else None,
                        elf=request.get("symbol_artifact") if isinstance(request.get("symbol_artifact"), str) else None,
                        max_iters=int(request.get("max_iters", 12)),
                        serial_read_seconds=float(request.get("serial_read_seconds", 3.0)),
                        workspace_root=request.get("workspace_root") if isinstance(request.get("workspace_root"), str) else None,
                        build_command=request.get("build_command") if isinstance(request.get("build_command"), str) else None,
                        event_sink=self.renderer.emit,
                    )
                )
            except BrainConfigError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.context.last_session_id = execution.result.session_id or self.renderer.current_session_id
            self.renderer.render_execution(execution)
            return True
        if mode == "benchmark":
            case_id = request.get("case_id")
            if not isinstance(case_id, str) or not case_id:
                self.renderer.print_refusal(
                    f"Refused [ux/invalid-request]: benchmark session `{session_id}` has no case_id."
                )
                return True
            try:
                report = run_benchmark_case(
                    case_id=case_id,
                    provider=request_provider,
                    model=model if isinstance(model, str) else None,
                    event_sink=self.renderer.emit,
                )
            except BrainConfigError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.context.last_session_id = report.session_id
            self.renderer.render_case_report(report)
            return True
        self.renderer.print_refusal(
            f"Refused [ux/invalid-request]: session `{session_id}` uses unsupported mode `{mode}`."
        )
        return True
