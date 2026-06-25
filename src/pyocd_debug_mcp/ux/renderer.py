"""Rich-based rendering for the operator-facing turnkey CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
from typing import Any, Literal

from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.text import Text

from pyocd_debug_mcp.brain.events import BrainEvent
from pyocd_debug_mcp.brain.loop import TurnkeyExecution
from pyocd_debug_mcp.ux.artifacts import ArtifactEntry, artifact_entries, preview_json, preview_text
from pyocd_debug_mcp.ux.history import HistoryEntry, SessionBundle

RawOutputPolicy = Literal["off", "final", "all"]


@dataclass
class UXRenderer:
    raw_output: RawOutputPolicy = "final"
    console: Console = field(default_factory=Console)

    def __post_init__(self) -> None:
        self._status: Status | None = None
        self._active_status_message: str | None = None
        self._last_provider_output: str | None = None
        self._current_session_id: str | None = None
        self._is_tty = bool(sys.stdout.isatty()) and self.console.is_terminal

    @property
    def current_session_id(self) -> str | None:
        return self._current_session_id

    def _start_status(self, message: str) -> None:
        self._active_status_message = message
        if not self._is_tty:
            self.console.print(f"[cyan]{message}[/cyan]")
            return
        self._stop_status()
        self._status = self.console.status(message, spinner="dots")
        self._status.start()

    def _stop_status(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None
        self._active_status_message = None

    def emit(self, event: BrainEvent) -> None:
        self._current_session_id = event.session_id or self._current_session_id
        details = event.details
        if event.event_kind in {"provider_turn_start", "tool_start", "build_start", "green_check_start"}:
            self._start_status(event.message)
            if event.event_kind == "tool_start":
                tool_name = details.get("tool_name", "(tool)")
                args = details.get("arguments", {})
                self.console.print(f"[bold cyan]tool[/bold cyan] {tool_name} {args}")
            return

        if event.event_kind in {"provider_turn_complete", "tool_complete", "build_complete", "green_check_complete"}:
            self._stop_status()

        if event.event_kind == "provider_turn_complete":
            decision = details.get("decision")
            if isinstance(decision, dict):
                self._render_decision_summary(decision)
            raw_output = details.get("raw_output")
            if isinstance(raw_output, str):
                self._last_provider_output = raw_output
                if self.raw_output == "all":
                    self.render_raw_output(raw_output)
            return

        if event.event_kind == "tool_complete":
            tool_name = details.get("tool_name", "(tool)")
            duration_ms = details.get("duration_ms")
            result_text = details.get("result_text")
            suffix = f" in {duration_ms} ms" if isinstance(duration_ms, int) else ""
            self.console.print(f"[green]done[/green] {tool_name}{suffix}")
            if isinstance(result_text, str) and result_text:
                excerpt = result_text if len(result_text) <= 220 else result_text[:220] + "..."
                self.console.print(f"  [dim]{excerpt}[/dim]")
            return

        if event.event_kind == "file_read":
            self.console.print(f"[cyan]read[/cyan] {details.get('path')}")
            return
        if event.event_kind == "file_replace":
            self.console.print(f"[yellow]replace[/yellow] {details.get('path')}")
            return
        if event.event_kind == "build_complete":
            self.console.print(f"[green]build[/green] {event.message}")
            return
        if event.event_kind == "green_check_complete":
            self.console.print(f"[green]verify[/green] {event.message}")
            return
        if event.event_kind == "verification_state_update":
            verification = details.get("verification")
            self.console.print(f"[blue]verification[/blue] {verification}")
            return
        if event.event_kind == "refusal":
            self.console.print(Panel(Text(event.message), border_style="yellow", title="Refusal"))
            return
        if event.event_kind == "block":
            self.console.print(Panel(Text(event.message), border_style="red", title="Blocked"))
            return
        if event.event_kind == "unexpected_failure":
            self.console.print(Panel(Text(event.message), border_style="red", title="Failure"))
            return
        if event.event_kind == "final_result":
            self.console.print(f"[bold green]{event.message}[/bold green]")
            return
        if event.event_kind == "session_state":
            self.console.print(f"[magenta]{event.message}[/magenta]")
            return
        if event.event_kind == "run_start":
            self.console.print(f"[bold]{event.message}[/bold]")

    def _render_decision_summary(self, decision: dict[str, Any]) -> None:
        action = decision.get("action")
        lines = [
            f"observation: {decision.get('observation_summary', '(none)')}",
            f"classification: {decision.get('classification', '(none)')}",
        ]
        hypothesis = decision.get("hypothesis")
        if hypothesis:
            lines.append(f"hypothesis: {hypothesis}")
        strategy = decision.get("strategy_evaluation")
        if strategy:
            lines.append(f"strategy: {strategy}")
        if isinstance(action, dict):
            lines.append(f"next action: {action.get('kind')} {action}")
        self.console.print(Panel("\n".join(lines), title="Evidence Summary", border_style="blue"))

    def render_raw_output(self, raw_output: str) -> None:
        self.console.print(Panel(raw_output, title="Raw Provider Output", border_style="magenta"))

    def render_execution(self, execution: TurnkeyExecution) -> None:
        self._stop_status()
        result = execution.result
        table = Table(show_header=False, box=None)
        table.add_row("board", result.board_id)
        table.add_row("session", result.session_id or "(none)")
        table.add_row("classification", result.classification)
        table.add_row("status", result.final_status)
        table.add_row("summary", result.summary)
        table.add_row("root_cause", result.root_cause)
        table.add_row(
            "verification",
            (
                f"flash={result.verification.flash_ok} "
                f"uart={result.verification.uart_ok} "
                f"symbol={result.verification.symbol_ok} "
                f"green={result.verification.green_check_ok}"
            ),
        )
        if execution.run_root is not None:
            table.add_row("run_root", str(execution.run_root))
        self.console.print(Panel(table, title="Run Result", border_style="green"))
        if self.raw_output == "final" and self._last_provider_output:
            self.render_raw_output(self._last_provider_output)

    def render_case_report(self, report: Any) -> None:
        label = report.score_report.outcome_label.upper()
        color = "green" if report.score_report.outcome_label == "full_success" else "yellow"
        self.console.print(
            f"[{color}][{label}][/{color}] {report.case_id} "
            f"score={report.score_report.score} session_id={report.session_id or '(missing)'}"
        )
        for reason in report.score_report.reasons:
            self.console.print(f"  [dim]- {reason}[/dim]")

    def render_suite_summary(self, suite_name: str, reports: list[Any]) -> None:
        full_success = sum(report.score_report.outcome_label == "full_success" for report in reports)
        partial_success = sum(report.score_report.outcome_label == "partial_success" for report in reports)
        failures = len(reports) - full_success - partial_success
        average = sum(report.score_report.score for report in reports) / len(reports) if reports else 0.0
        self.console.print(
            Panel(
                (
                    f"Suite {suite_name}\n"
                    f"full_success={full_success}\n"
                    f"partial_success={partial_success}\n"
                    f"fail={failures}\n"
                    f"average_score={average:.1f}"
                ),
                title="Benchmark Summary",
                border_style="green" if failures == 0 else "yellow",
            )
        )

    def render_history(self, entries: list[HistoryEntry]) -> None:
        table = Table(title="Recent Sessions")
        table.add_column("session_id", style="cyan")
        table.add_column("board")
        table.add_column("provider")
        table.add_column("mode")
        table.add_column("status")
        table.add_column("summary")
        for entry in entries:
            table.add_row(
                entry.session_id,
                entry.board_id or "(unknown)",
                entry.provider or "(unknown)",
                entry.run_mode or "(unknown)",
                entry.final_status or "(unknown)",
                entry.task_summary or "(none)",
            )
        self.console.print(table)

    def render_session_bundle(self, bundle: SessionBundle) -> None:
        request = bundle.request or {}
        result = bundle.result or {}
        table = Table(show_header=False, box=None)
        table.add_row("session_id", bundle.session_id)
        table.add_row("run_root", str(bundle.run_root))
        table.add_row("board_id", str(request.get("board_id", "(unknown)")))
        table.add_row("provider", str(request.get("provider", "(unknown)")))
        table.add_row("model", str(request.get("model", "(default)")))
        table.add_row("mode", str(request.get("mode", "(unknown)")))
        table.add_row("case_id", str(request.get("case_id", "(none)")))
        table.add_row("task", str(request.get("task", "(none)")))
        table.add_row("final_status", str(result.get("final_status", "(unknown)")))
        table.add_row("classification", str(result.get("classification", "(unknown)")))
        table.add_row("summary", str(result.get("summary", "(none)")))
        self.console.print(Panel(table, title="Saved Run", border_style="blue"))
        self.render_artifacts(bundle, preview=False)

    def render_artifacts(self, bundle: SessionBundle, *, preview: bool = True) -> None:
        table = Table(title=f"Artifacts for {bundle.session_id}")
        table.add_column("label", style="cyan")
        table.add_column("path")
        for entry in artifact_entries(bundle):
            table.add_row(entry.label, str(entry.path))
        self.console.print(table)
        if not preview:
            return
        for entry in artifact_entries(bundle):
            self.render_artifact_entry(entry)

    def render_artifact_entry(self, entry: ArtifactEntry, *, title: str | None = None) -> None:
        if entry.path.suffix == ".json":
            self.console.print(Panel(preview_json(entry.path), title=title or entry.label, border_style="blue"))
        elif entry.path.suffix in {".txt", ".jsonl", ".diff"}:
            self.console.print(Panel(preview_text(entry.path), title=title or entry.label, border_style="blue"))

    def print_info(self, message: str) -> None:
        self.console.print(message)

    def print_error(self, message: str) -> None:
        self.console.print(Panel(Text(message), title="Error", border_style="red"))

    def print_refusal(self, message: str) -> None:
        self.console.print(Panel(Text(message), title="Refused", border_style="yellow"))

    def show_last_raw(self) -> None:
        if self._last_provider_output is None:
            self.print_error("No provider output has been recorded in this shell yet.")
            return
        self.render_raw_output(self._last_provider_output)
