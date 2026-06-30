"""Shared provider contracts and canonical memory helpers for turnkey backends."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Literal, Protocol, cast

from pyocd_debug_mcp.brain.actions import TurnDecision

ProviderContinuationMode = Literal["remote-primary", "local-primary"]
ProviderContinuationPath = Literal[
    "remote-resume",
    "remote-fork",
    "local-memory-fallback",
    "local-memory-only",
    "summary-call",
]
ProviderRemoteStrategy = Literal[
    "openai-response-chain",
    "claude-session-resume",
    "codex-thread-resume",
    "none",
]
ProviderMemoryMode = Literal["deterministic", "model-summary"]
ProviderResumeRecoveryChoice = Literal["retry", "new-session-from-memory", "abort"]
ProviderMemoryResultStatus = Literal["success", "failure", "refusal", "block", "unknown"]

DEFAULT_RECENT_TURN_LIMIT = 4  # PROJECT-DEFINED (hybrid memory recent-turn window)
DEFAULT_RECENT_RENDER_CHAR_LIMIT = 8_000  # PROJECT-DEFINED (recent-memory prompt cap)
DEFAULT_SUMMARY_CHAR_LIMIT = 4_000  # PROJECT-DEFINED (compacted-summary prompt cap)
DEFAULT_NATIVE_SYNC_EVERY = 10  # PROJECT-DEFINED (remote safety-sync cadence)
RESUME_RECOVERY_ACTION_METADATA_KEY = "resume_recovery_action"  # PROJECT-DEFINED
RESUME_RECOVERY_FAILURE_METADATA_KEY = "resume_recovery_failure"  # PROJECT-DEFINED

_ENTRY_FIELD_CHAR_LIMIT = 320
_SUMMARY_COMPONENT_CHAR_LIMIT = 180


class _KeepSentinel:
    pass


_KEEP = _KeepSentinel()


@dataclass(frozen=True)
class ProviderCapabilities:
    # The legacy boolean fields remain for compatibility with older tests and
    # diagnostics. The canonical runtime contract is continuation_mode plus
    # remote_strategy.
    supports_native_session: bool
    supports_transcript_continuation: bool
    supports_response_id_continuation: bool
    supports_tool_schema_prompt: bool
    continuation_mode: ProviderContinuationMode
    remote_strategy: ProviderRemoteStrategy = "none"
    resume_requires_stable_workdir: bool = False
    supports_transactional_fork: bool = False
    supports_partial_streaming: bool = False

    def to_record(self) -> dict[str, object]:
        return {
            "supports_native_session": self.supports_native_session,
            "supports_transcript_continuation": self.supports_transcript_continuation,
            "supports_response_id_continuation": self.supports_response_id_continuation,
            "supports_tool_schema_prompt": self.supports_tool_schema_prompt,
            "continuation_mode": self.continuation_mode,
            "remote_strategy": self.remote_strategy,
            "resume_requires_stable_workdir": self.resume_requires_stable_workdir,
            "supports_transactional_fork": self.supports_transactional_fork,
            "supports_partial_streaming": self.supports_partial_streaming,
        }


@dataclass(frozen=True)
class ProviderRuntimeContext:
    runtime_root: str
    working_directory: str
    transport_metadata: dict[str, object] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "runtime_root": self.runtime_root,
            "working_directory": self.working_directory,
            "transport_metadata": dict(self.transport_metadata),
        }

    def summary_record(self) -> dict[str, object]:
        return {
            "runtime_root": self.runtime_root,
            "working_directory": self.working_directory,
            "transport_metadata_keys": sorted(self.transport_metadata),
        }


@dataclass(frozen=True)
class ProviderNativeHandle:
    native_session_id: str | None = None
    response_id: str | None = None
    provider_fields: dict[str, object] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "native_session_id": self.native_session_id,
            "response_id": self.response_id,
            "provider_fields": dict(self.provider_fields),
        }

    def summary_record(self) -> dict[str, object]:
        return {
            "native_session_id": self.native_session_id,
            "response_id": self.response_id,
            "provider_field_keys": sorted(self.provider_fields),
        }


@dataclass(frozen=True)
class ProviderMemoryEntry:
    turn_index: int
    classification: str | None
    observation_summary: str
    hypothesis: str | None
    action_kind: str
    action_summary: str
    result_summary: str
    verification_snapshot: str
    decision_rationale: str | None = None
    action_payload: dict[str, object] = field(default_factory=dict)
    result_status: ProviderMemoryResultStatus = "unknown"
    artifact_paths: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    codebase_summary: str | None = None
    failed_hypotheses: tuple[str, ...] = ()
    refused_or_blocked_paths: tuple[str, ...] = ()
    acceptance_constraints: tuple[str, ...] = ()

    def to_record(self) -> dict[str, object]:
        return {
            "turn_index": self.turn_index,
            "classification": self.classification,
            "observation_summary": self.observation_summary,
            "hypothesis": self.hypothesis,
            "action_kind": self.action_kind,
            "action_summary": self.action_summary,
            "result_summary": self.result_summary,
            "verification_snapshot": self.verification_snapshot,
            "decision_rationale": self.decision_rationale,
            "action_payload": dict(self.action_payload),
            "result_status": self.result_status,
            "artifact_paths": list(self.artifact_paths),
            "changed_files": list(self.changed_files),
            "codebase_summary": self.codebase_summary,
            "failed_hypotheses": list(self.failed_hypotheses),
            "refused_or_blocked_paths": list(self.refused_or_blocked_paths),
            "acceptance_constraints": list(self.acceptance_constraints),
        }

    def render_text(self) -> str:
        lines = [
            f"[turn {self.turn_index}]",
            f"classification: {self.classification or '(none)'}",
            f"observation: {_trim_text(self.observation_summary, _ENTRY_FIELD_CHAR_LIMIT)}",
            f"action: {self.action_kind} | {_trim_text(self.action_summary, _ENTRY_FIELD_CHAR_LIMIT)}",
            f"result: {_trim_text(self.result_summary, _ENTRY_FIELD_CHAR_LIMIT)}",
            f"result_status: {self.result_status}",
            f"verification: {_trim_text(self.verification_snapshot, _ENTRY_FIELD_CHAR_LIMIT)}",
        ]
        if self.hypothesis:
            lines.insert(
                3,
                f"hypothesis: {_trim_text(self.hypothesis, _ENTRY_FIELD_CHAR_LIMIT)}",
            )
        if self.decision_rationale:
            lines.insert(
                4 if self.hypothesis else 3,
                f"rationale: {_trim_text(self.decision_rationale, _ENTRY_FIELD_CHAR_LIMIT)}",
            )
        if self.changed_files:
            lines.append("changed_files: " + ", ".join(self.changed_files[:5]))
        if self.refused_or_blocked_paths:
            lines.append("blocked_or_refused: " + ", ".join(self.refused_or_blocked_paths[:5]))
        if self.codebase_summary:
            lines.append(f"codebase: {_trim_text(self.codebase_summary, _ENTRY_FIELD_CHAR_LIMIT)}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ProviderResumeFailureRecord:
    provider: str
    remote_strategy: ProviderRemoteStrategy
    continuation_mode: ProviderContinuationMode
    continuation_path: ProviderContinuationPath
    remote_handle_kind: str
    expected_handle_id: str
    turn_index: int
    failure_text: str
    local_memory_available: bool
    replacement_provider_session_started: bool = False

    def to_record(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "remote_strategy": self.remote_strategy,
            "continuation_mode": self.continuation_mode,
            "continuation_path": self.continuation_path,
            "remote_handle_kind": self.remote_handle_kind,
            "expected_handle_id": self.expected_handle_id,
            "turn_index": self.turn_index,
            "failure_text": self.failure_text,
            "local_memory_available": self.local_memory_available,
            "replacement_provider_session_started": self.replacement_provider_session_started,
        }


class ProviderResumeFailure(RuntimeError):
    """Raised when a real provider handle exists but cannot be resumed."""

    def __init__(self, record: ProviderResumeFailureRecord) -> None:
        super().__init__(
            f"{record.provider} failed to resume {record.remote_handle_kind}="
            f"{record.expected_handle_id}: {record.failure_text}"
        )
        self.record = record

    def to_record(self) -> dict[str, object]:
        return self.record.to_record()


@dataclass(frozen=True)
class ProviderMemorySummary:
    mode: ProviderMemoryMode
    summary_text: str
    covered_through_turn: int
    source: str
    char_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "summary_text": self.summary_text,
            "covered_through_turn": self.covered_through_turn,
            "source": self.source,
            "char_count": self.char_count,
        }


@dataclass(frozen=True)
class ProviderMemorySummaryResult:
    summary_text: str
    provider_metadata: dict[str, object] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "summary_text": self.summary_text,
            "provider_metadata": dict(self.provider_metadata),
        }


@dataclass(frozen=True)
class ProviderMemoryCompactionPlan:
    evicted_entries: tuple[ProviderMemoryEntry, ...]
    retained_entries: tuple[ProviderMemoryEntry, ...]
    rendered_recent_char_count: int

    def to_record(self) -> dict[str, object]:
        return {
            "evicted_turns": [entry.turn_index for entry in self.evicted_entries],
            "retained_turns": [entry.turn_index for entry in self.retained_entries],
            "rendered_recent_char_count": self.rendered_recent_char_count,
        }


@dataclass(frozen=True)
class ProviderSessionState:
    provider: str
    model: str | None
    memory_mode: ProviderMemoryMode
    continuation_mode: ProviderContinuationMode
    runtime_context: ProviderRuntimeContext | None = None
    native_handle: ProviderNativeHandle | None = None
    recent_memory_entries: tuple[ProviderMemoryEntry, ...] = ()
    memory_summary: ProviderMemorySummary | None = None
    recent_turn_limit: int = DEFAULT_RECENT_TURN_LIMIT
    recent_render_char_limit: int = DEFAULT_RECENT_RENDER_CHAR_LIMIT
    summary_char_limit: int = DEFAULT_SUMMARY_CHAR_LIMIT
    native_sync_every: int = DEFAULT_NATIVE_SYNC_EVERY
    turns_since_last_memory_sync: int = 0
    last_continuation_path: ProviderContinuationPath | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "memory_mode": self.memory_mode,
            "continuation_mode": self.continuation_mode,
            "runtime_context": (
                self.runtime_context.to_record() if self.runtime_context is not None else None
            ),
            "native_handle": self.native_handle.to_record()
            if self.native_handle is not None
            else None,
            "recent_turn_limit": self.recent_turn_limit,
            "recent_render_char_limit": self.recent_render_char_limit,
            "summary_char_limit": self.summary_char_limit,
            "native_sync_every": self.native_sync_every,
            "turns_since_last_memory_sync": self.turns_since_last_memory_sync,
            "last_continuation_path": self.last_continuation_path,
            "recent_memory_entries": [entry.to_record() for entry in self.recent_memory_entries],
            "memory_summary": self.memory_summary.to_record()
            if self.memory_summary is not None
            else None,
            "metadata": dict(self.metadata),
        }

    def summary_record(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "memory_mode": self.memory_mode,
            "continuation_mode": self.continuation_mode,
            "runtime_context": (
                self.runtime_context.summary_record() if self.runtime_context is not None else None
            ),
            "native_handle": (
                self.native_handle.summary_record() if self.native_handle is not None else None
            ),
            "recent_memory_entry_count": len(self.recent_memory_entries),
            "recent_memory_render_char_count": len(
                _render_recent_memory_entries(self.recent_memory_entries)
            ),
            "memory_summary": (
                {
                    "covered_through_turn": self.memory_summary.covered_through_turn,
                    "source": self.memory_summary.source,
                    "char_count": self.memory_summary.char_count,
                }
                if self.memory_summary is not None
                else None
            ),
            "native_sync_every": self.native_sync_every,
            "turns_since_last_memory_sync": self.turns_since_last_memory_sync,
            "last_continuation_path": self.last_continuation_path,
            "metadata": dict(self.metadata),
        }

    def with_runtime_context(
        self, runtime_context: ProviderRuntimeContext
    ) -> "ProviderSessionState":
        return replace(self, runtime_context=runtime_context)

    def with_updated_metadata(
        self, metadata: dict[str, object] | None = None
    ) -> "ProviderSessionState":
        merged = dict(self.metadata)
        if metadata is not None:
            merged.update(metadata)
        return replace(self, metadata=merged)

    def with_runtime_transport_metadata(
        self,
        transport_metadata: dict[str, object],
    ) -> "ProviderSessionState":
        if self.runtime_context is None:
            return self
        merged = dict(self.runtime_context.transport_metadata)
        merged.update(transport_metadata)
        return replace(
            self,
            runtime_context=replace(self.runtime_context, transport_metadata=merged),
        )

    def with_native_handle_update(
        self,
        *,
        response_id: str | None | _KeepSentinel = _KEEP,
        native_session_id: str | None | _KeepSentinel = _KEEP,
        provider_fields: dict[str, object] | None = None,
    ) -> "ProviderSessionState":
        if (
            response_id is _KEEP
            and native_session_id is _KEEP
            and provider_fields is None
            and self.native_handle is None
        ):
            return self
        existing = self.native_handle or ProviderNativeHandle()
        merged_fields = dict(existing.provider_fields)
        if provider_fields is not None:
            merged_fields.update(provider_fields)
        if native_session_id is _KEEP:
            resolved_native_session_id: str | None = existing.native_session_id
        else:
            resolved_native_session_id = cast(str | None, native_session_id)
        if response_id is _KEEP:
            resolved_response_id: str | None = existing.response_id
        else:
            resolved_response_id = cast(str | None, response_id)
        next_handle = ProviderNativeHandle(
            native_session_id=resolved_native_session_id,
            response_id=resolved_response_id,
            provider_fields=merged_fields,
        )
        if (
            next_handle.native_session_id is None
            and next_handle.response_id is None
            and not next_handle.provider_fields
        ):
            return replace(self, native_handle=None)
        return replace(self, native_handle=next_handle)

    def with_last_continuation_path(
        self,
        path: ProviderContinuationPath,
        *,
        metadata: dict[str, object] | None = None,
    ) -> "ProviderSessionState":
        merged = dict(self.metadata)
        if metadata is not None:
            merged.update(metadata)
        return replace(self, last_continuation_path=path, metadata=merged)

    def with_memory_state(
        self,
        *,
        recent_memory_entries: tuple[ProviderMemoryEntry, ...] | None = None,
        memory_summary: ProviderMemorySummary | None | _KeepSentinel = _KEEP,
        turns_since_last_memory_sync: int | None = None,
        metadata: dict[str, object] | None = None,
    ) -> "ProviderSessionState":
        merged = dict(self.metadata)
        if metadata is not None:
            merged.update(metadata)
        if memory_summary is _KEEP:
            resolved_memory_summary: ProviderMemorySummary | None = self.memory_summary
        else:
            resolved_memory_summary = cast(ProviderMemorySummary | None, memory_summary)
        return replace(
            self,
            recent_memory_entries=(
                self.recent_memory_entries
                if recent_memory_entries is None
                else recent_memory_entries
            ),
            memory_summary=resolved_memory_summary,
            turns_since_last_memory_sync=(
                self.turns_since_last_memory_sync
                if turns_since_last_memory_sync is None
                else turns_since_last_memory_sync
            ),
            metadata=merged,
        )

    def next_turn_index(self) -> int:
        covered = self.memory_summary.covered_through_turn if self.memory_summary is not None else 0
        if not self.recent_memory_entries:
            return covered + 1
        return max(entry.turn_index for entry in self.recent_memory_entries) + 1


@dataclass(frozen=True)
class ProviderPromptBundle:
    system_instructions: str
    tool_schema_text: str
    provider_memory_text: str
    turn_context_text: str
    turn_decision_schema_text: str
    skill_context_text: str = ""

    def _join_user_sections(self, *sections: str) -> str:
        return "\n\n".join(section for section in (part.strip() for part in sections) if section)

    def render_bootstrap_text(self, *, include_memory: bool = True) -> str:
        sections = [
            self.skill_context_text.strip(),
            self.tool_schema_text.strip(),
            self.turn_context_text.strip(),
        ]
        if include_memory and self.provider_memory_text.strip():
            sections.append(self.provider_memory_text.strip())
        sections.append(self.turn_decision_schema_text.strip())
        return self._join_user_sections(*sections)

    def render_remote_delta_text(self) -> str:
        return self._join_user_sections(self.turn_context_text)

    def render_remote_sync_text(self, *, include_memory: bool = True) -> str:
        return self.render_bootstrap_text(include_memory=include_memory)

    def render_retry_text(self, correction_note: str) -> str:
        return self._join_user_sections(
            self.turn_context_text,
            self.turn_decision_schema_text,
            correction_note,
        )

    def user_prompt_text(self, *, include_memory: bool = True) -> str:
        return self.render_bootstrap_text(include_memory=include_memory)

    def full_prompt_text(self, *, include_memory: bool = True) -> str:
        return (
            f"{self.system_instructions.strip()}\n\n"
            f"{self.render_bootstrap_text(include_memory=include_memory).strip()}\n"
        )

    def to_record(self) -> dict[str, object]:
        return {
            "system_instruction_length": len(self.system_instructions),
            "skill_context_length": len(self.skill_context_text),
            "tool_schema_length": len(self.tool_schema_text),
            "provider_memory_length": len(self.provider_memory_text),
            "turn_context_length": len(self.turn_context_text),
            "turn_decision_schema_length": len(self.turn_decision_schema_text),
        }


@dataclass(frozen=True)
class ProviderProgressUpdate:
    stage: str
    message: str
    details: dict[str, object] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "message": self.message,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class ProviderTurn:
    decision: TurnDecision
    output_text: str
    response_id: str | None
    session_state: ProviderSessionState
    provider_metadata: dict[str, object] = field(default_factory=dict)
    progress_updates: tuple[ProviderProgressUpdate, ...] = ()


class DecisionProvider(Protocol):
    @property
    def capabilities(self) -> ProviderCapabilities: ...

    async def next_decision(
        self,
        *,
        prompt_bundle: ProviderPromptBundle,
        session_state: ProviderSessionState,
    ) -> ProviderTurn: ...

    async def summarize_memory(
        self,
        *,
        session_state: ProviderSessionState,
        prior_summary_text: str,
        evicted_entries: tuple[ProviderMemoryEntry, ...],
    ) -> ProviderMemorySummaryResult: ...


def make_provider_session_state(
    *,
    provider: str,
    model: str | None,
    memory_mode: ProviderMemoryMode = "deterministic",
    continuation_mode: ProviderContinuationMode = "local-primary",
    native_sync_every: int = DEFAULT_NATIVE_SYNC_EVERY,
    runtime_context: ProviderRuntimeContext | None = None,
    metadata: dict[str, object] | None = None,
) -> ProviderSessionState:
    return ProviderSessionState(
        provider=provider,
        model=model,
        memory_mode=memory_mode,
        continuation_mode=continuation_mode,
        native_sync_every=native_sync_every,
        runtime_context=runtime_context,
        metadata=dict(metadata or {}),
    )


def provider_resume_recovery_action(
    session_state: ProviderSessionState,
) -> ProviderResumeRecoveryChoice | None:
    action = session_state.metadata.get(RESUME_RECOVERY_ACTION_METADATA_KEY)
    if action in {"retry", "new-session-from-memory", "abort"}:
        return cast(ProviderResumeRecoveryChoice, action)
    return None


def with_provider_resume_recovery_request(
    session_state: ProviderSessionState,
    *,
    action: ProviderResumeRecoveryChoice,
    failure: ProviderResumeFailureRecord,
) -> ProviderSessionState:
    return session_state.with_updated_metadata(
        {
            RESUME_RECOVERY_ACTION_METADATA_KEY: action,
            RESUME_RECOVERY_FAILURE_METADATA_KEY: failure.to_record(),
        }
    )


def clear_provider_resume_recovery_request(
    session_state: ProviderSessionState,
) -> ProviderSessionState:
    return session_state.with_updated_metadata(
        {
            RESUME_RECOVERY_ACTION_METADATA_KEY: None,
            RESUME_RECOVERY_FAILURE_METADATA_KEY: None,
        }
    )


def provider_turn_record(provider_turn: ProviderTurn) -> dict[str, object]:
    return {
        "response_id": provider_turn.response_id,
        "provider_metadata": dict(provider_turn.provider_metadata),
        "session_state": provider_turn.session_state.summary_record(),
        "progress_updates": [update.to_record() for update in provider_turn.progress_updates],
    }


def build_provider_turn_metadata(
    *,
    capabilities: ProviderCapabilities,
    continuation_path: ProviderContinuationPath,
    prompt_render_mode: str,
    memory_injected: bool,
    static_tool_schema_injected: bool,
    decision_schema_injected: bool,
    retry_count: int,
    remote_handle_kind: str,
    remote_handle_id: str | None,
    fresh_remote_turn: bool,
    resumed_remote: bool,
    native_sync_used: bool = False,
    working_directory: str | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "continuation_mode": capabilities.continuation_mode,
        "remote_strategy": capabilities.remote_strategy,
        "continuation_path": continuation_path,
        "prompt_render_mode": prompt_render_mode,
        "memory_injected": memory_injected,
        "static_tool_schema_injected": static_tool_schema_injected,
        "decision_schema_injected": decision_schema_injected,
        "retry_count": retry_count,
        "remote_handle_kind": remote_handle_kind,
        "remote_handle_id": remote_handle_id,
        "remote_handle_present": remote_handle_id is not None,
        "fresh_remote_turn": fresh_remote_turn,
        "resumed_remote": resumed_remote,
        "native_sync_used": native_sync_used,
        "local_memory_fallback_used": continuation_path == "local-memory-fallback",
    }
    if working_directory is not None:
        metadata["working_directory"] = working_directory
    if extra is not None:
        metadata.update(extra)
    return metadata


def provider_has_local_memory(session_state: ProviderSessionState) -> bool:
    return bool(session_state.recent_memory_entries or session_state.memory_summary)


def render_recent_memory_entries(
    entries: tuple[ProviderMemoryEntry, ...],
    *,
    char_limit: int,
) -> str:
    return _render_recent_memory_entries(entries, char_limit=char_limit)


def _render_recent_memory_entries(
    entries: tuple[ProviderMemoryEntry, ...],
    *,
    char_limit: int | None = None,
) -> str:
    if not entries:
        return ""
    blocks: list[str] = []
    for entry in entries:
        block = entry.render_text()
        tentative = "\n\n".join((*blocks, block))
        if char_limit is not None and len(tentative) > char_limit and blocks:
            break
        if char_limit is not None and len(tentative) > char_limit:
            blocks.append(_trim_text(block, char_limit))
            break
        blocks.append(block)
    return "\n\n".join(blocks)


def render_provider_memory_text(session_state: ProviderSessionState) -> str:
    sections: list[str] = []
    if (
        session_state.memory_summary is not None
        and session_state.memory_summary.summary_text.strip()
    ):
        sections.append(
            "Compacted prior turn facts:\n" + session_state.memory_summary.summary_text.strip()
        )
    recent_text = render_recent_memory_entries(
        session_state.recent_memory_entries,
        char_limit=session_state.recent_render_char_limit,
    )
    if recent_text:
        sections.append("Recent committed turn facts:\n" + recent_text)
    if not sections:
        return ""
    return "\n\n".join(("Provider session memory:", *sections))


def should_inject_native_memory_sync(session_state: ProviderSessionState) -> bool:
    return (
        session_state.native_sync_every > 0
        and provider_has_local_memory(session_state)
        and session_state.turns_since_last_memory_sync >= session_state.native_sync_every
    )


def append_memory_entry(
    session_state: ProviderSessionState,
    entry: ProviderMemoryEntry,
) -> ProviderSessionState:
    return replace(
        session_state,
        recent_memory_entries=(*session_state.recent_memory_entries, entry),
    )


def plan_memory_compaction(
    session_state: ProviderSessionState,
) -> ProviderMemoryCompactionPlan | None:
    retained = list(session_state.recent_memory_entries)
    evicted: list[ProviderMemoryEntry] = []
    rendered_char_count = len(_render_recent_memory_entries(tuple(retained)))
    if (
        len(retained) <= session_state.recent_turn_limit
        and rendered_char_count <= session_state.recent_render_char_limit
    ):
        return None
    while len(retained) > session_state.recent_turn_limit:
        evicted.append(retained.pop(0))
    rendered_char_count = len(_render_recent_memory_entries(tuple(retained)))
    while retained and rendered_char_count > session_state.recent_render_char_limit:
        evicted.append(retained.pop(0))
        rendered_char_count = len(_render_recent_memory_entries(tuple(retained)))
    return ProviderMemoryCompactionPlan(
        evicted_entries=tuple(evicted),
        retained_entries=tuple(retained),
        rendered_recent_char_count=rendered_char_count,
    )


def apply_deterministic_compaction(
    session_state: ProviderSessionState,
    plan: ProviderMemoryCompactionPlan,
    *,
    source: str = "deterministic",
) -> ProviderSessionState:
    merged_lines = _merged_summary_lines(
        existing_summary=session_state.memory_summary.summary_text
        if session_state.memory_summary
        else "",
        new_lines=[_deterministic_summary_line(entry) for entry in plan.evicted_entries],
        char_limit=session_state.summary_char_limit,
    )
    summary_text = "\n".join(merged_lines)
    if plan.evicted_entries:
        covered_through_turn = plan.evicted_entries[-1].turn_index
    else:
        covered_through_turn = (
            session_state.memory_summary.covered_through_turn
            if session_state.memory_summary is not None
            else 0
        )
    summary = ProviderMemorySummary(
        mode=session_state.memory_mode,
        summary_text=summary_text,
        covered_through_turn=covered_through_turn,
        source=source,
        char_count=len(summary_text),
    )
    return replace(
        session_state,
        recent_memory_entries=plan.retained_entries,
        memory_summary=summary,
    )


def apply_summary_compaction(
    session_state: ProviderSessionState,
    plan: ProviderMemoryCompactionPlan,
    *,
    summary_text: str,
    source: str,
) -> ProviderSessionState:
    normalized_summary = _trim_summary_text(
        summary_text, char_limit=session_state.summary_char_limit
    )
    if plan.evicted_entries:
        covered_through_turn = plan.evicted_entries[-1].turn_index
    else:
        covered_through_turn = (
            session_state.memory_summary.covered_through_turn
            if session_state.memory_summary is not None
            else 0
        )
    summary = ProviderMemorySummary(
        mode=session_state.memory_mode,
        summary_text=normalized_summary,
        covered_through_turn=covered_through_turn,
        source=source,
        char_count=len(normalized_summary),
    )
    return replace(
        session_state,
        recent_memory_entries=plan.retained_entries,
        memory_summary=summary,
    )


def advance_memory_sync_state(
    session_state: ProviderSessionState,
    *,
    memory_rendered_this_turn: bool,
) -> ProviderSessionState:
    next_count = 0 if memory_rendered_this_turn else session_state.turns_since_last_memory_sync + 1
    return replace(session_state, turns_since_last_memory_sync=next_count)


def render_memory_summary_request(
    *,
    prior_summary_text: str,
    evicted_entries: tuple[ProviderMemoryEntry, ...],
    summary_char_limit: int,
) -> str:
    lines = [
        "Compact the prior firmware-debugging turn history into one durable summary.",
        "",
        "Return exactly one JSON object with this shape:",
        '{"summary_text": "<compact summary>"}',
        "",
        "Requirements:",
        f"- Keep summary_text at or under {summary_char_limit} characters.",
        "- Preserve only durable facts that matter for future diagnosis and repair.",
        "- Prefer concrete observations, hypotheses, actions, results, and verification deltas.",
        "- Do not restate tool schemas, system rules, or the current-turn prompt.",
        "- Do not mention that you are summarizing; output only factual memory content.",
        "",
        "Prior compacted summary:",
        prior_summary_text.strip() or "(none)",
        "",
        "Evicted committed turn facts:",
        render_recent_memory_entries(evicted_entries, char_limit=24_000) or "(none)",
    ]
    return "\n".join(lines)


def _trim_text(text: str | None, limit: int) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    if limit <= 3:
        return value[:limit]
    return value[: limit - 3].rstrip() + "..."


def _deterministic_summary_line(entry: ProviderMemoryEntry) -> str:
    components = [
        f"turn {entry.turn_index}",
        f"class={entry.classification or '(none)'}",
        f"obs={_trim_text(entry.observation_summary, _SUMMARY_COMPONENT_CHAR_LIMIT)}",
    ]
    if entry.hypothesis:
        components.append(f"hyp={_trim_text(entry.hypothesis, _SUMMARY_COMPONENT_CHAR_LIMIT)}")
    components.append(
        f"action={entry.action_kind}:{_trim_text(entry.action_summary, _SUMMARY_COMPONENT_CHAR_LIMIT)}"
    )
    components.append(f"result={_trim_text(entry.result_summary, _SUMMARY_COMPONENT_CHAR_LIMIT)}")
    components.append(
        f"verify={_trim_text(entry.verification_snapshot, _SUMMARY_COMPONENT_CHAR_LIMIT)}"
    )
    return "- " + "; ".join(components)


def _merged_summary_lines(
    *,
    existing_summary: str,
    new_lines: list[str],
    char_limit: int,
) -> list[str]:
    lines = [line for line in existing_summary.splitlines() if line.strip()]
    lines.extend(line for line in new_lines if line.strip())
    while lines and len("\n".join(lines)) > char_limit:
        lines.pop(0)
    return lines


def _trim_summary_text(text: str, *, char_limit: int) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    while lines and len("\n".join(lines)) > char_limit:
        lines.pop(0)
    return "\n".join(lines)
