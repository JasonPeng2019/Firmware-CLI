"""Live provider-native skill invocation proof harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import tempfile
from functools import partial
from typing import Any, Literal, Sequence, cast

import anyio

from pyocd_debug_mcp.brain.actions import LoadSkillsAction, decision_schema_text
from pyocd_debug_mcp.brain.provider_claude_cli import ClaudeCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_codex_cli import CodexCLIDecisionProvider
from pyocd_debug_mcp.brain.provider_native_skills import (
    ProviderNativeSkillProjection,
    prepare_provider_native_skill_projection,
)
from pyocd_debug_mcp.brain.provider_types import (
    ProviderPromptBundle,
    ProviderRuntimeContext,
    ProviderSessionState,
)

ProviderName = Literal["codex-cli", "claude-cli"]
PROOF_SKILL_ID = "firmcli-native-usage-proof"


def write_usage_proof_skill(source_root: Path, *, token: str) -> Path:
    """Create a temporary provider-native proof skill."""
    skill_root = source_root / "common" / PROOF_SKILL_ID
    skill_root.mkdir(parents=True, exist_ok=True)
    skill_root.joinpath("skill.yaml").write_text(
        "\n".join(
            [
                f"skill_id: {PROOF_SKILL_ID}",
                "title: FirmCLI Native Usage Proof",
                "description: Use only to prove provider-native skill invocation.",
                "providers:",
                "  - claude-cli",
                "  - codex-cli",
                "native_invocation:",
                f"  claude-cli: /{PROOF_SKILL_ID}",
                f"  codex-cli: ${PROOF_SKILL_ID}",
                "fallback_skill_ids:",
                "  - firmcli-firmware-debug",
                "depends_on: []",
                "context_files:",
                "  - SKILL.md",
                "usable_paths: []",
                "requires_governed_actions: []",
                "source_status: active",
                "",
            ]
        ),
        encoding="utf-8",
    )
    skill_root.joinpath("SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {PROOF_SKILL_ID}",
                "description: Reveals a one-time FirmCLI native skill usage proof token.",
                "---",
                "",
                "# FirmCLI Native Usage Proof",
                "",
                "When this provider-native skill is invoked, return the exact proof token below",
                "inside the FirmCLI TurnDecision root_cause or summary.",
                "",
                f"PROOF_TOKEN={token}",
                "",
                "Do not run board tools. Do not request load_skills. Return a normal FirmCLI",
                "finalize decision that includes this token.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return skill_root


def build_usage_prompt_bundle(
    *,
    provider: ProviderName,
    projection: ProviderNativeSkillProjection,
) -> ProviderPromptBundle:
    invocation = projection.manifests[0].invocation_for(provider)
    return ProviderPromptBundle(
        system_instructions=(
            "You are validating FirmCLI provider-native skill invocation. "
            "Return only one JSON object matching the FirmCLI TurnDecision schema."
        ),
        tool_schema_text="",
        provider_memory_text="",
        native_skill_context_text=projection.prompt_text(),
        turn_context_text=(
            "Validation task: use the provider-native skill "
            f"`{PROOF_SKILL_ID}` through its native invocation `{invocation}`. "
            "The proof token is not present in this prompt. It is only inside the "
            "native skill body. Do not inspect files directly and do not request "
            "`load_skills`; this proof must demonstrate native skill access. "
            "After using the native skill, return a finalize action with "
            "final_status=`diagnosed_only`, classification=`healthy`, and include "
            "the exact proof token in root_cause or summary. If you cannot access "
            "the native skill, return finalize with final_status=`blocked` and do "
            "not invent a token."
        ),
        turn_decision_schema_text=decision_schema_text(),
        native_skill_projection=projection.to_record(),
        native_skill_tool_allowlist=projection.claude_allowed_tools,
    )


async def run_usage_proof(
    *,
    provider: ProviderName,
    timeout_seconds: float,
    report_root: Path,
) -> dict[str, Any]:
    token = (
        f"FIRMCLI_NATIVE_SKILL_USAGE_{provider.replace('-', '_').upper()}_{secrets.token_hex(4)}"
    )
    with tempfile.TemporaryDirectory(prefix=f"firmcli-native-skill-{provider}-") as tmpdir:
        temp_root = Path(tmpdir)
        source_root = temp_root / "client-owned-provider-native"
        runtime_root = temp_root / "runtime"
        working_directory = temp_root / "workspace"
        write_usage_proof_skill(source_root, token=token)
        projection = prepare_provider_native_skill_projection(
            provider=provider,
            mode="require",
            source_root=source_root,
            runtime_root=runtime_root,
            working_directory=working_directory,
        )
        bundle = build_usage_prompt_bundle(provider=provider, projection=projection)
        state = ProviderSessionState(
            provider=provider,
            model=None,
            memory_mode="deterministic",
            continuation_mode="remote-primary",
            runtime_context=ProviderRuntimeContext(
                runtime_root=str(runtime_root),
                working_directory=str(working_directory),
                transport_metadata={"usage_proof": True},
            ),
        )
        provider_client = (
            CodexCLIDecisionProvider(model=None, timeout_seconds=timeout_seconds)
            if provider == "codex-cli"
            else ClaudeCLIDecisionProvider(model=None, timeout_seconds=timeout_seconds)
        )
        provider_turn = await provider_client.next_decision(
            prompt_bundle=bundle,
            session_state=state,
        )
        decision = provider_turn.decision
        action = decision.action
        action_kind = getattr(action, "kind", None)
        decision_text = json.dumps(decision.model_dump(mode="json"), sort_keys=True)
        token_observed = token in decision_text
        fallback_used = isinstance(action, LoadSkillsAction)
        passed = bool(
            projection.enabled
            and token_observed
            and action_kind == "finalize"
            and not fallback_used
        )
        report = {
            "provider": provider,
            "passed": passed,
            "token": token,
            "token_observed": token_observed,
            "fallback_used": fallback_used,
            "action_kind": action_kind,
            "projection": projection.to_record(),
            "decision": decision.model_dump(mode="json"),
            "provider_metadata": provider_turn.provider_metadata,
            "output_text": provider_turn.output_text,
        }
        report_root.mkdir(parents=True, exist_ok=True)
        report_path = report_root / f"{provider}-provider-native-skill-usage.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report["report_path"] = str(report_path)
        return report


async def run_all(
    *,
    providers: Sequence[ProviderName],
    timeout_seconds: float,
    report_root: Path,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for provider in providers:
        results.append(
            await run_usage_proof(
                provider=provider,
                timeout_seconds=timeout_seconds,
                report_root=report_root,
            )
        )
    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove provider-native skill invocation for Codex/Claude CLI."
    )
    parser.add_argument(
        "--provider",
        action="append",
        choices=["codex-cli", "claude-cli"],
        required=True,
        help="Provider to test. Repeat for multiple providers.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument(
        "--report-root",
        type=Path,
        default=Path("runs") / "provider-native-skill-usage",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    providers: tuple[ProviderName, ...] = tuple(
        cast(ProviderName, provider) for provider in args.provider
    )
    results = anyio.run(
        partial(
            run_all,
            providers=providers,
            timeout_seconds=args.timeout_seconds,
            report_root=args.report_root,
        )
    )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
