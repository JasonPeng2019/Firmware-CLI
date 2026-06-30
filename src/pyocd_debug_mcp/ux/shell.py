"""Interactive operator shell for the turnkey brain."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import anyio
from prompt_toolkit import PromptSession
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.patch_stdout import patch_stdout

if sys.platform == "win32":  # pragma: no cover - Windows import path only
    from prompt_toolkit.output.win32 import (
        NoConsoleScreenBufferError as _NoConsoleScreenBufferError,
    )
else:  # pragma: no cover - non-Windows hosts
    _NO_CONSOLE_ERROR_TYPE: type[BaseException] = RuntimeError
    _NO_CONSOLE_ERRORS: tuple[type[BaseException], ...] = (_NO_CONSOLE_ERROR_TYPE,)

if sys.platform == "win32":  # pragma: no cover - Windows import path only
    _NO_CONSOLE_ERRORS = (_NoConsoleScreenBufferError,)

from pyocd_debug_mcp.brain.app import run_benchmark_case, run_benchmark_suite, run_freeform_task
from pyocd_debug_mcp.brain.config import (
    BrainConfigError,
    DEFAULT_TURNKEY_NATIVE_SYNC_EVERY,
    TurnkeyMemoryMode,
    TurnkeyProviderKind,
    cast_provider,
    cast_memory_mode,
    resolve_memory_mode,
    resolve_native_sync_every,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderResumeFailure,
    ProviderResumeRecoveryChoice,
)
from pyocd_debug_mcp.ux.artifacts import find_shortcut_entries
from pyocd_debug_mcp.ux.commands import (
    HELP_TEXT,
    ShellCommandError,
    SlashCommand,
    TaskInput,
    parse_shell_input,
)
from pyocd_debug_mcp.ux.history import (
    SessionBundle,
    UXHistoryError,
    load_session_bundle,
    list_history,
)
from pyocd_debug_mcp.ux.renderer import RawOutputPolicy, UXRenderer


@dataclass(frozen=True)
class GuidedCommandSpec:
    name: str
    help_text: str
    base_task_template: str
    required_context_fields: tuple[str, ...] = ()
    use_workspace_context: bool = False
    extra_prefix: str = "Additional operator context:"

    def build_task(self, *, board_id: str, extra_text: str | None) -> str:
        task = self.base_task_template.format(board_id=board_id)
        normalized_extra = _normalize_command_text(extra_text)
        if normalized_extra:
            task = f"{task}\n\n{self.extra_prefix} {normalized_extra}"
        return task


GUIDED_COMMANDS: dict[str, GuidedCommandSpec] = {
    "verify": GuidedCommandSpec(
        name="verify",
        help_text="Verify the current firmware/target behavior and explain whether it is healthy.",
        base_task_template=(
            "Verify the current firmware/target behavior on board {board_id}. "
            "Treat this as a reference health check: gather board evidence, determine whether the "
            "current image is healthy, and explain why. Do not edit source files."
        ),
    ),
    "diagnose": GuidedCommandSpec(
        name="diagnose",
        help_text="Diagnose the current board/runtime problem and recommend the next action.",
        base_task_template=(
            "Diagnose the current firmware/target problem on board {board_id}. "
            "Classify the likely root cause from the available board evidence, explain why, and "
            "recommend the next action. Do not edit source files."
        ),
    ),
    "repair": GuidedCommandSpec(
        name="repair",
        help_text="Diagnose, repair, rebuild, reflash, and re-verify the current problem.",
        base_task_template=(
            "Diagnose the current firmware/target problem on board {board_id}, repair it if needed, "
            "rebuild, reflash, and re-verify the result. Prefer the minimal correct change and explain "
            "the final evidence."
        ),
        required_context_fields=("workspace_root", "build_command"),
        use_workspace_context=True,
    ),
}

ARTIFACT_SHORTCUTS = ("prompt", "diff", "serial", "score", "events")

CONTEXT_COMMAND_HELP: dict[str, str] = {
    "workspace_root": "/workspace <path>",
    "build_command": '/build-command "<cmd>"',
}


def _normalize_command_text(text: str | None) -> str | None:
    if text is None:
        return None
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return value or None


@dataclass
class ShellContext:
    board_id: str | None = None
    provider: TurnkeyProviderKind | None = None
    model: str | None = None
    last_session_id: str | None = None
    raw_output: RawOutputPolicy = "off"
    memory_mode: TurnkeyMemoryMode = "deterministic"
    native_sync_every: int = DEFAULT_TURNKEY_NATIVE_SYNC_EVERY
    workspace_root: str | None = None
    build_command: str | None = None
    flash_artifact: str | None = None
    symbol_artifact: str | None = None

    def prompt_text(self) -> str:
        board = self.board_id or "board?"
        provider = self.provider or "provider:auto"
        model = self.model or "model:default"
        session = self.last_session_id or "session:-"
        return f"[{board}][{provider}][{model}][{session}] > "


class OperatorShell:
    def __init__(self, renderer: UXRenderer | None = None) -> None:
        self.renderer = renderer or UXRenderer(raw_output="off")
        self.context = ShellContext(
            raw_output=self.renderer.raw_output,
            memory_mode=resolve_memory_mode(),
            native_sync_every=resolve_native_sync_every(),
        )
        self._session: PromptSession[str] = self._build_prompt_session()

    @staticmethod
    def _build_prompt_session() -> PromptSession[str]:
        try:
            return PromptSession()
        except _NO_CONSOLE_ERRORS:
            return PromptSession(output=DummyOutput())

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
            return self._run_task(parsed.task, use_workspace_context=True)
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
        if command.name == "memory-mode":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /memory-mode <deterministic|model-summary>")
                return True
            try:
                self.context.memory_mode = cast_memory_mode(command.args[0])
            except BrainConfigError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.renderer.print_info(f"Memory mode set to {self.context.memory_mode}.")
            return True
        if command.name == "native-sync-every":
            if len(command.args) != 1:
                self.renderer.print_error("Usage: /native-sync-every <0|N>")
                return True
            try:
                value = int(command.args[0])
            except ValueError:
                self.renderer.print_refusal(
                    "Refused [ux/invalid-native-sync]: native sync cadence must be 0 or a positive integer."
                )
                return True
            if value < 0:
                self.renderer.print_refusal(
                    "Refused [ux/invalid-native-sync]: native sync cadence must be 0 or a positive integer."
                )
                return True
            self.context.native_sync_every = value
            self.renderer.print_info(
                f"Native sync cadence set to {self.context.native_sync_every}."
            )
            return True
        if command.name == "workspace":
            return self._handle_workspace_command(command)
        if command.name == "build-command":
            return self._handle_build_command(command)
        if command.name == "flash-artifact":
            return self._handle_file_context_command(
                command,
                attribute="flash_artifact",
                usage="Usage: /flash-artifact <path|default>",
                label="Flash artifact",
            )
        if command.name == "elf":
            return self._handle_file_context_command(
                command,
                attribute="symbol_artifact",
                usage="Usage: /elf <path|default>",
                label="ELF symbol artifact",
            )
        if command.name == "run":
            task = _normalize_command_text(command.arg_text)
            if task is None:
                self.renderer.print_error("Usage: /run <task>")
                return True
            return self._run_task(task, use_workspace_context=True)
        if command.name in GUIDED_COMMANDS:
            return self._run_guided_command(GUIDED_COMMANDS[command.name], command)
        if command.name == "benchmark":
            if len(command.args) != 2 or command.args[0] not in {"case", "suite"}:
                self.renderer.print_error(
                    "Usage: /benchmark case <case_id> | /benchmark suite <suite_name>"
                )
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
            session_id = command.args[0] if command.args else None
            return self._render_artifacts(session_id)
        if command.name in ARTIFACT_SHORTCUTS:
            session_id = command.args[0] if command.args else None
            return self._render_artifact_shortcut(command.name, session_id)
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

    def _handle_workspace_command(self, command: SlashCommand) -> bool:
        raw_value = _normalize_command_text(command.arg_text)
        if raw_value is None:
            self.renderer.print_info(f"Workspace root: {self.context.workspace_root or '(unset)'}")
            return True
        if raw_value == "clear":
            self.context.workspace_root = None
            self.renderer.print_info("Workspace root cleared.")
            return True
        path = Path(raw_value).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            self.renderer.print_refusal(
                f"Refused [ux/invalid-workspace]: workspace root does not exist or is not a directory: {path}"
            )
            return True
        self.context.workspace_root = str(path)
        self.renderer.print_info(f"Workspace root set to {self.context.workspace_root}.")
        return True

    def _handle_build_command(self, command: SlashCommand) -> bool:
        raw_value = _normalize_command_text(command.arg_text)
        if raw_value is None:
            self.renderer.print_info(f"Build command: {self.context.build_command or '(unset)'}")
            return True
        if raw_value == "clear":
            self.context.build_command = None
            self.renderer.print_info("Build command cleared.")
            return True
        self.context.build_command = raw_value
        self.renderer.print_info(f"Build command set to {self.context.build_command}.")
        return True

    def _handle_file_context_command(
        self,
        command: SlashCommand,
        *,
        attribute: str,
        usage: str,
        label: str,
    ) -> bool:
        current_value = getattr(self.context, attribute)
        raw_value = _normalize_command_text(command.arg_text)
        if raw_value is None:
            self.renderer.print_info(f"{label}: {current_value or '(default)'}")
            return True
        if raw_value == "default":
            setattr(self.context, attribute, None)
            self.renderer.print_info(f"{label} reset to default resolution.")
            return True
        path = Path(raw_value).expanduser().resolve()
        if not path.exists() or not path.is_file():
            self.renderer.print_refusal(
                f"Refused [ux/missing-artifact]: {label.lower()} does not exist or is not a file: {path}"
            )
            return True
        setattr(self.context, attribute, str(path))
        self.renderer.print_info(f"{label} set to {path}.")
        return True

    def _run_guided_command(self, spec: GuidedCommandSpec, command: SlashCommand) -> bool:
        if self.context.board_id is None:
            self.renderer.print_error("Select a board first with `/board <id>`.")
            return True
        for field_name in spec.required_context_fields:
            if getattr(self.context, field_name) is None:
                guidance = CONTEXT_COMMAND_HELP.get(field_name, field_name)
                self.renderer.print_refusal(
                    f"Refused [ux/missing-repair-context]: `/{spec.name}` requires {guidance} to be set first."
                )
                return True
        task = spec.build_task(board_id=self.context.board_id, extra_text=command.arg_text)
        return self._run_task(task, use_workspace_context=spec.use_workspace_context)

    def _run_task(self, task: str, *, use_workspace_context: bool) -> bool:
        if self.context.board_id is None:
            self.renderer.print_error("Select a board first with `/board <id>`.")
            return True
        workspace_root = self.context.workspace_root if use_workspace_context else None
        build_command = self.context.build_command if use_workspace_context else None
        try:
            execution = anyio.run(
                lambda: run_freeform_task(
                    board_id=self.context.board_id or "",
                    task=task,
                    provider=self.context.provider,
                    model=self.context.model,
                    memory_mode=self.context.memory_mode,
                    native_sync_every=self.context.native_sync_every,
                    flash_artifact=self.context.flash_artifact,
                    elf=self.context.symbol_artifact,
                    workspace_root=workspace_root,
                    build_command=build_command,
                    event_sink=self.renderer.emit,
                    provider_resume_recovery=self._prompt_provider_resume_recovery,
                )
            )
        except BrainConfigError as exc:
            self.renderer.print_error(str(exc))
            return True
        self.context.last_session_id = (
            execution.result.session_id or self.renderer.current_session_id
        )
        self.renderer.render_execution(execution)
        return True

    def _run_benchmark_case(self, case_id: str) -> bool:
        try:
            report = run_benchmark_case(
                case_id=case_id,
                provider=self.context.provider,
                model=self.context.model,
                memory_mode=self.context.memory_mode,
                native_sync_every=self.context.native_sync_every,
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
                memory_mode=self.context.memory_mode,
                native_sync_every=self.context.native_sync_every,
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

    def _render_artifacts(self, session_id: str | None) -> bool:
        bundle = self._load_selected_bundle(session_id)
        if bundle is None:
            return True
        self.renderer.render_artifacts(bundle)
        self.context.last_session_id = bundle.session_id
        return True

    def _render_artifact_shortcut(self, shortcut: str, session_id: str | None) -> bool:
        bundle = self._load_selected_bundle(session_id)
        if bundle is None:
            return True
        entries = find_shortcut_entries(bundle, shortcut)
        if not entries:
            self.renderer.print_refusal(
                f"Refused [ux/missing-artifact]: session `{bundle.session_id}` has no artifact for `/{shortcut}`."
            )
            return True
        for entry in entries:
            self.renderer.render_artifact_entry(entry, title=f"{shortcut}: {entry.label}")
        self.context.last_session_id = bundle.session_id
        return True

    def _load_selected_bundle(self, session_id: str | None) -> SessionBundle | None:
        selected_session_id = self._select_session_id(session_id)
        if selected_session_id is None:
            self.renderer.print_error(
                "No session selected. Run something first or pass an explicit session id."
            )
            return None
        try:
            return load_session_bundle(selected_session_id)
        except UXHistoryError as exc:
            self.renderer.print_error(str(exc))
            return None

    def _select_session_id(self, session_id: str | None) -> str | None:
        if session_id:
            return session_id
        if self.context.last_session_id:
            return self.context.last_session_id
        history = list_history(limit=1)
        if history.entries:
            return history.entries[0].session_id
        return None

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
            native_sync_every = request.get("native_sync_every")
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
                        memory_mode=(
                            cast_memory_mode(str(request.get("memory_mode")))
                            if isinstance(request.get("memory_mode"), str)
                            else None
                        ),
                        native_sync_every=native_sync_every
                        if isinstance(native_sync_every, int)
                        else None,
                        port=request.get("port_override")
                        if isinstance(request.get("port_override"), str)
                        else None,
                        flash_artifact=request.get("flash_artifact")
                        if isinstance(request.get("flash_artifact"), str)
                        else None,
                        elf=request.get("symbol_artifact")
                        if isinstance(request.get("symbol_artifact"), str)
                        else None,
                        max_iters=int(request.get("max_iters", 12)),
                        serial_read_seconds=float(request.get("serial_read_seconds", 3.0)),
                        workspace_root=request.get("workspace_root")
                        if isinstance(request.get("workspace_root"), str)
                        else None,
                        build_command=request.get("build_command")
                        if isinstance(request.get("build_command"), str)
                        else None,
                        event_sink=self.renderer.emit,
                        provider_resume_recovery=self._prompt_provider_resume_recovery,
                    )
                )
            except BrainConfigError as exc:
                self.renderer.print_error(str(exc))
                return True
            self.context.last_session_id = (
                execution.result.session_id or self.renderer.current_session_id
            )
            self.renderer.render_execution(execution)
            return True
        if mode == "benchmark":
            case_id = request.get("case_id")
            native_sync_every = request.get("native_sync_every")
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
                    memory_mode=(
                        cast_memory_mode(str(request.get("memory_mode")))
                        if isinstance(request.get("memory_mode"), str)
                        else None
                    ),
                    native_sync_every=native_sync_every
                    if isinstance(native_sync_every, int)
                    else None,
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

    def _prompt_provider_resume_recovery(
        self,
        failure: ProviderResumeFailure,
    ) -> ProviderResumeRecoveryChoice:
        record = failure.record
        self.renderer.print_error("Provider session resume failed.")
        self.renderer.print_info(f"Provider: {record.provider}")
        self.renderer.print_info(
            f"Expected {record.remote_handle_kind}: {record.expected_handle_id}"
        )
        self.renderer.print_info("No new provider session has been started.")
        while True:
            choice = (
                self._session.prompt(
                    "[r] retry resume   [n] new session from saved memory   [a] abort > "
                )
                .strip()
                .lower()
            )
            if choice in {"r", "retry"}:
                return "retry"
            if choice in {"n", "new"}:
                return "new-session-from-memory"
            if choice in {"a", "abort"}:
                return "abort"
            self.renderer.print_error("Choose r, n, or a.")
