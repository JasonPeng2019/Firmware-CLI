"""In-memory state model for one turnkey run."""

from __future__ import annotations

from dataclasses import dataclass, field

from pyocd_debug_mcp.brain.actions import Classification, VerificationSnapshot
from pyocd_debug_mcp.brain.evidence import (
    Experiment,
    Hypothesis,
    Observation,
    StrategyEvaluation,
)
from pyocd_debug_mcp.timeouts import (
    ServerTimeoutUpdate,
    TurnkeyTimeoutConfig,
    default_turnkey_timeout_config,
    server_timeout_update_to_record,
)


@dataclass
class BrainState:
    run_mode: str
    board_id: str
    task: str
    case_id: str | None
    case_kind: str | None
    selected_skill_ids: tuple[str, ...]
    iteration: int = 0
    session_id: str | None = None
    session_ids_seen: list[str] = field(default_factory=list)
    probe_uid: str | None = None
    route_used: str | None = None
    board_info: str | None = None
    flash_count: int = 0
    build_count: int = 0
    recover_count: int = 0
    last_classification: Classification | None = None
    last_action_summary: str | None = None
    last_observation_text: str | None = None
    last_result_text: str | None = None
    actions_taken: list[str] = field(default_factory=list)
    mcp_tools_used: list[str] = field(default_factory=list)
    recover_used: bool = False
    verification: VerificationSnapshot = field(default_factory=VerificationSnapshot)
    blocked_action_families: set[str] = field(default_factory=set)
    refused_action_families: set[str] = field(default_factory=set)
    no_progress_streak: int = 0
    repeated_build_failure_count: int = 0
    stagnant_fix_cycle_count: int = 0
    pending_fix_evaluation: bool = False
    effective_timeout_config: TurnkeyTimeoutConfig = field(default_factory=default_turnkey_timeout_config)
    effective_max_iters: int = 0
    pending_server_timeout_sync: ServerTimeoutUpdate | None = None
    last_timeout_policy: dict[str, object] | None = None
    last_build_failure_signature: str | None = None
    last_no_progress_signature: str | None = None
    last_verification_signature: tuple[bool, bool, bool, bool] | None = None
    observations: list[Observation] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    experiments: list[Experiment] = field(default_factory=list)
    strategy_evaluations: list[StrategyEvaluation] = field(default_factory=list)

    def register_connect(
        self,
        *,
        session_id: str | None,
        probe_uid: str | None,
        route_used: str | None,
    ) -> None:
        self.session_id = session_id
        self.probe_uid = probe_uid
        self.route_used = route_used
        if session_id and session_id not in self.session_ids_seen:
            self.session_ids_seen.append(session_id)

    def register_tool_use(self, tool_name: str) -> None:
        self.mcp_tools_used.append(tool_name)
        if tool_name == "flash_firmware":
            self.flash_count += 1
        elif tool_name == "unlock_recover":
            self.recover_count += 1

    def register_disconnect(self) -> None:
        self.session_id = None
        self.probe_uid = None
        self.route_used = None

    def register_build(self) -> None:
        self.build_count += 1

    def verification_signature(self) -> tuple[bool, bool, bool, bool]:
        snapshot = self.verification
        return (
            snapshot.flash_ok,
            snapshot.uart_ok,
            snapshot.symbol_ok,
            snapshot.green_check_ok,
        )

    def to_record(self) -> dict[str, object]:
        return {
            "run_mode": self.run_mode,
            "board_id": self.board_id,
            "task": self.task,
            "case_id": self.case_id,
            "case_kind": self.case_kind,
            "selected_skill_ids": list(self.selected_skill_ids),
            "iteration": self.iteration,
            "session_id": self.session_id,
            "session_ids_seen": list(self.session_ids_seen),
            "probe_uid": self.probe_uid,
            "route_used": self.route_used,
            "board_info": self.board_info,
            "flash_count": self.flash_count,
            "build_count": self.build_count,
            "recover_count": self.recover_count,
            "last_classification": self.last_classification,
            "last_action_summary": self.last_action_summary,
            "last_observation_text": self.last_observation_text,
            "last_result_text": self.last_result_text,
            "actions_taken": list(self.actions_taken),
            "mcp_tools_used": list(self.mcp_tools_used),
            "recover_used": self.recover_used,
            "verification": self.verification.model_dump(),
            "blocked_action_families": sorted(self.blocked_action_families),
            "refused_action_families": sorted(self.refused_action_families),
            "no_progress_streak": self.no_progress_streak,
            "repeated_build_failure_count": self.repeated_build_failure_count,
            "stagnant_fix_cycle_count": self.stagnant_fix_cycle_count,
            "pending_fix_evaluation": self.pending_fix_evaluation,
            "effective_timeout_config": self.effective_timeout_config.to_record(),
            "effective_max_iters": self.effective_max_iters,
            "pending_server_timeout_sync": server_timeout_update_to_record(
                self.pending_server_timeout_sync
            ),
            "last_timeout_policy": self.last_timeout_policy,
            "observations": [item.to_dict() for item in self.observations],
            "hypotheses": [item.to_dict() for item in self.hypotheses],
            "experiments": [item.to_dict() for item in self.experiments],
            "strategy_evaluations": [item.to_dict() for item in self.strategy_evaluations],
        }
