"""Artifact discovery and preview helpers for the operator-facing CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pyocd_debug_mcp.ux.history import SessionBundle

ARTIFACT_SHORTCUT_LABELS: dict[str, tuple[str, ...]] = {
    "prompt": ("prompt",),
    "diff": ("turnkey_diff", "agent_diff"),
    "serial": ("final_serial_excerpt",),
    "score": ("score",),
    "events": ("brain_events", "server_events"),
}


@dataclass(frozen=True)
class ArtifactEntry:
    label: str
    path: Path


def artifact_entries(bundle: SessionBundle) -> list[ArtifactEntry]:
    run_root = bundle.run_root
    candidates = [
        ("session", run_root / "run-metadata" / "session.json"),
        ("turnkey_request", run_root / "run-metadata" / "turnkey_request.json"),
        ("turnkey_result", run_root / "run-metadata" / "turnkey_result.json"),
        ("turnkey_state", run_root / "run-metadata" / "turnkey_state.json"),
        ("benchmark_case", run_root / "run-metadata" / "benchmark_case.json"),
        ("benchmark_result", run_root / "run-metadata" / "benchmark_result.json"),
        ("score", run_root / "run-metadata" / "score.json"),
        ("firmware_identity", run_root / "run-metadata" / "firmware_identity.json"),
        ("server_events", run_root / "logs" / "events.jsonl"),
        ("brain_events", run_root / "logs" / "brain_events.jsonl"),
        ("brain_trace", run_root / "logs" / "brain_trace.jsonl"),
        ("model_turns", run_root / "logs" / "model_turns.jsonl"),
        ("prompt", run_root / "logs" / "prompt.txt"),
        ("turnkey_diff", run_root / "applied-patches" / "turnkey.diff"),
        ("agent_diff", run_root / "applied-patches" / "agent.diff"),
        ("final_serial_excerpt", run_root / "captured-serial" / "final_excerpt.txt"),
    ]
    return [ArtifactEntry(label=label, path=path) for label, path in candidates if path.exists()]


def find_artifact_entry(bundle: SessionBundle, label: str) -> ArtifactEntry | None:
    for entry in artifact_entries(bundle):
        if entry.label == label:
            return entry
    return None


def find_shortcut_entries(bundle: SessionBundle, shortcut: str) -> tuple[ArtifactEntry, ...]:
    labels = ARTIFACT_SHORTCUT_LABELS.get(shortcut, ())
    return tuple(
        entry for label in labels if (entry := find_artifact_entry(bundle, label)) is not None
    )


def preview_text(path: Path, *, max_lines: int = 24, max_chars: int = 5000) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    clipped = raw[:max_chars]
    lines = clipped.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["..."]
    return "\n".join(lines)


def preview_json(path: Path, *, max_chars: int = 5000) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[:max_chars] + "\n..."
