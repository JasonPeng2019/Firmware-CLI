"""Shared probe inventory and board-aware selection helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from pyocd_debug_mcp.board_config import BoardConfig, PROBE_FAMILY_HINTS

RunCommand = Callable[[list[str]], tuple[int, str, str]]

_ROW_RE = re.compile(
    r"^\s*(?P<index>\d+)\s{2,}(?P<description>.+?)\s{2,}(?P<uid>\S+)\s{2,}(?P<state>\S.*)?$"
)


@dataclass(frozen=True)
class ProbeInfo:
    uid: str
    description: str
    raw: str
    state: str = ""

    @property
    def searchable_text(self) -> str:
        return f"{self.uid} {self.description} {self.raw}".lower()


@dataclass(frozen=True)
class ProbeResolution:
    probe: ProbeInfo | None
    note: str
    probes: tuple[ProbeInfo, ...]


def parse_pyocd_probe_listing(output: str) -> list[ProbeInfo]:
    """Parse `pyocd list --probes` table output into structured rows."""

    probes: list[ProbeInfo] = []
    current_index: int | None = None

    for line in output.splitlines():
        raw = line.rstrip()
        stripped = raw.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if (
            stripped.startswith("#")
            or lowered.startswith("probe/board")
            or lowered.startswith("no available debug probes")
            or re.fullmatch(r"-+", stripped)
        ):
            continue

        match = _ROW_RE.match(raw)
        if match:
            probe = ProbeInfo(
                uid=match.group("uid").strip(),
                description=match.group("description").strip(),
                state=(match.group("state") or "").strip(),
                raw=raw,
            )
            probes.append(probe)
            current_index = len(probes) - 1
            continue

        if current_index is not None:
            current = probes[current_index]
            probes[current_index] = ProbeInfo(
                uid=current.uid,
                description=f"{current.description} {stripped}".strip(),
                state=current.state,
                raw=f"{current.raw}\n{raw}",
            )

    return probes


def list_connected_probes(run_cmd: RunCommand) -> list[ProbeInfo]:
    """Return the connected probes visible to pyOCD."""

    rc, out, _ = run_cmd(["pyocd", "list", "--probes"])
    if rc != 0 or not out.strip():
        return []
    return parse_pyocd_probe_listing(out)


def _score_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def pick_probe_for_board(
    board: BoardConfig,
    probes: list[ProbeInfo],
    *,
    allow_single_fallback: bool,
) -> ProbeResolution:
    """Select one connected probe for a tracked board."""

    if not probes:
        return ProbeResolution(probe=None, note="no probes detected", probes=tuple())

    scored: list[tuple[int, ProbeInfo]] = []
    for probe in probes:
        score = _score_terms(probe.searchable_text, board.probe_hint_terms)
        if score > 0:
            scored.append((score, probe))

    if scored:
        best_score = max(score for score, _ in scored)
        best = [probe for score, probe in scored if score == best_score]
        if len(best) == 1:
            return ProbeResolution(probe=best[0], note="", probes=tuple(probes))
        return ProbeResolution(
            probe=None,
            note="multiple matching probes found; disconnect extras or refine probe_hint_terms",
            probes=tuple(probes),
        )

    if allow_single_fallback and len(probes) == 1:
        probe = probes[0]
        family_terms = tuple(PROBE_FAMILY_HINTS.get(board.probe_family, set()))
        if family_terms and _score_terms(probe.searchable_text, family_terms) > 0:
            return ProbeResolution(
                probe=probe,
                note="single connected probe assumed for this board",
                probes=tuple(probes),
            )
        return ProbeResolution(
            probe=None,
            note="single connected probe does not match the expected probe family",
            probes=tuple(probes),
        )

    return ProbeResolution(
        probe=None,
        note="no matching probe found",
        probes=tuple(probes),
    )


def resolve_probe_for_board(
    board: BoardConfig,
    *,
    run_cmd: RunCommand,
    allow_single_fallback: bool,
) -> ProbeResolution:
    """List probes and select the best match for the given board."""

    probes = list_connected_probes(run_cmd)
    return pick_probe_for_board(
        board,
        probes,
        allow_single_fallback=allow_single_fallback,
    )
