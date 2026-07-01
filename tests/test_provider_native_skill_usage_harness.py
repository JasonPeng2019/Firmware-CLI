from __future__ import annotations

from pathlib import Path

from tests.harness.provider_native_skill_usage import (
    PROOF_SKILL_ID,
    build_usage_prompt_bundle,
    write_usage_proof_skill,
)
from pyocd_debug_mcp.brain.provider_native_skills import prepare_provider_native_skill_projection


def test_usage_proof_skill_keeps_token_out_of_projection_prompt(tmp_path: Path) -> None:
    token = "FIRMCLI_NATIVE_SKILL_USAGE_TEST_SECRET"
    source_root = tmp_path / "source"
    write_usage_proof_skill(source_root, token=token)

    projection = prepare_provider_native_skill_projection(
        provider="codex-cli",
        mode="require",
        source_root=source_root,
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "workspace",
    )
    bundle = build_usage_prompt_bundle(provider="codex-cli", projection=projection)

    assert projection.enabled
    assert PROOF_SKILL_ID in bundle.native_skill_context_text
    assert token not in projection.prompt_text()
    assert token not in bundle.render_bootstrap_text()
    assert token in (
        tmp_path / "workspace" / ".codex" / "skills" / PROOF_SKILL_ID / "SKILL.md"
    ).read_text(encoding="utf-8")


def test_usage_proof_claude_bundle_carries_skill_allowlist(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    write_usage_proof_skill(source_root, token="FIRMCLI_NATIVE_SKILL_USAGE_TEST")

    projection = prepare_provider_native_skill_projection(
        provider="claude-cli",
        mode="require",
        source_root=source_root,
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "workspace",
    )
    bundle = build_usage_prompt_bundle(provider="claude-cli", projection=projection)

    assert projection.layout == ".claude/skills"
    assert bundle.native_skill_tool_allowlist == (f"Skill({PROOF_SKILL_ID})",)
    assert f"/{PROOF_SKILL_ID}" in bundle.native_skill_context_text
