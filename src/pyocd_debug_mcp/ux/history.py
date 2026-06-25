"""Run-history loading helpers for the operator-facing turnkey shell."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyocd_debug_mcp.services.session_runtime import RUNS_ROOT


class UXHistoryError(RuntimeError):
    """Raised when the UX layer cannot load a saved run."""


@dataclass(frozen=True)
class HistoryWarning:
    session_id: str
    message: str


@dataclass(frozen=True)
class HistoryEntry:
    session_id: str
    run_root: Path
    board_id: str | None
    provider: str | None
    model: str | None
    run_mode: str | None
    final_status: str | None
    case_id: str | None
    task_summary: str | None
    created_at: str | None


@dataclass(frozen=True)
class SessionBundle:
    session_id: str
    run_root: Path
    request: dict[str, Any] | None
    result: dict[str, Any] | None
    state: dict[str, Any] | None
    session: dict[str, Any] | None
    score: dict[str, Any] | None
    benchmark_case: dict[str, Any] | None
    benchmark_result: dict[str, Any] | None
    firmware_identity: dict[str, Any] | None


@dataclass(frozen=True)
class HistoryListing:
    entries: tuple[HistoryEntry, ...]
    warnings: tuple[HistoryWarning, ...]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UXHistoryError(f"{path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise UXHistoryError(f"{path} must contain a JSON object.")
    return payload


def _request_summary(request: dict[str, Any] | None) -> str | None:
    if request is None:
        return None
    case_id = request.get("case_id")
    if isinstance(case_id, str) and case_id:
        return case_id
    task = request.get("task")
    if isinstance(task, str) and task.strip():
        return task.strip()
    return None


def find_run_root(session_id: str, *, runs_root: Path = RUNS_ROOT) -> Path:
    run_root = runs_root / session_id
    if not run_root.is_dir():
        raise UXHistoryError(f"No run directory exists for session `{session_id}`.")
    return run_root


def load_session_bundle(session_id: str, *, runs_root: Path = RUNS_ROOT) -> SessionBundle:
    run_root = find_run_root(session_id, runs_root=runs_root)
    metadata = run_root / "run-metadata"
    return SessionBundle(
        session_id=session_id,
        run_root=run_root,
        request=_read_json(metadata / "turnkey_request.json"),
        result=_read_json(metadata / "turnkey_result.json"),
        state=_read_json(metadata / "turnkey_state.json"),
        session=_read_json(metadata / "session.json"),
        score=_read_json(metadata / "score.json"),
        benchmark_case=_read_json(metadata / "benchmark_case.json"),
        benchmark_result=_read_json(metadata / "benchmark_result.json"),
        firmware_identity=_read_json(metadata / "firmware_identity.json"),
    )


def list_history(*, runs_root: Path = RUNS_ROOT, limit: int | None = 20) -> HistoryListing:
    entries: list[HistoryEntry] = []
    warnings: list[HistoryWarning] = []
    for child in runs_root.iterdir() if runs_root.exists() else ():
        if not child.is_dir():
            continue
        metadata = child / "run-metadata"
        if not (metadata / "turnkey_request.json").exists():
            continue
        try:
            bundle = load_session_bundle(child.name, runs_root=runs_root)
        except UXHistoryError as exc:
            warnings.append(HistoryWarning(session_id=child.name, message=str(exc)))
            continue
        request = bundle.request
        result = bundle.result
        session = bundle.session
        created_at = session.get("created_at") if session else None
        entries.append(
            HistoryEntry(
                session_id=child.name,
                run_root=child,
                board_id=(request.get("board_id") if request else None),
                provider=(request.get("provider") if request else None),
                model=(request.get("model") if request else None),
                run_mode=(request.get("mode") if request else None),
                final_status=(result.get("final_status") if result else None),
                case_id=(request.get("case_id") if request else None),
                task_summary=_request_summary(request),
                created_at=created_at if isinstance(created_at, str) else None,
            )
        )
    entries.sort(
        key=lambda entry: (entry.created_at or entry.session_id, entry.session_id),
        reverse=True,
    )
    trimmed = entries[:limit] if limit is not None else entries
    return HistoryListing(entries=tuple(trimmed), warnings=tuple(warnings))
