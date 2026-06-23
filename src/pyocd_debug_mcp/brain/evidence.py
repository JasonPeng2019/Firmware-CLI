"""Typed evidence records captured during one turnkey run."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Observation:
    """One concrete observed fact captured during the loop."""

    observation_id: str
    source: str
    summary: str
    evidence_excerpt: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Hypothesis:
    """A suspected explanation that the loop is testing."""

    hypothesis_id: str
    summary: str
    status: str
    supporting_observation_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Experiment:
    """A deliberate intervention taken to validate or repair the system."""

    experiment_id: str
    purpose: str
    action_summary: str
    result: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyEvaluation:
    """A higher-level judgment about the loop's current approach."""

    strategy_id: str
    outcome: str
    next_action: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
