from __future__ import annotations

from pathlib import Path

import pytest

from pyocd_debug_mcp.brain.provider_native_skills import (
    PROJECTION_MARKER_NAME,
    ProviderNativeSkillError,
    load_provider_native_skill_manifests,
    prepare_provider_native_skill_projection,
)


def _write_provider_native_skill(
    root: Path,
    skill_id: str = "firmcli-test-skill",
    *,
    providers: tuple[str, ...] = ("claude-cli", "codex-cli"),
    context_files: tuple[str, ...] = ("SKILL.md",),
) -> Path:
    skill_root = root / "common" / skill_id
    skill_root.mkdir(parents=True)
    skill_root.joinpath("skill.yaml").write_text(
        "\n".join(
            [
                f"skill_id: {skill_id}",
                "title: Test Skill",
                "description: Test native provider skill.",
                "providers:",
                *(f"  - {provider}" for provider in providers),
                "native_invocation:",
                "  claude-cli: /firmcli-test-skill",
                "  codex-cli: $firmcli-test-skill",
                "fallback_skill_ids:",
                "  - firmcli-firmware-debug",
                "depends_on: []",
                "context_files:",
                *(f"  - {path}" for path in context_files),
                "usable_paths: []",
                "requires_governed_actions:",
                "  - connect",
                "source_status: active",
                "",
            ]
        ),
        encoding="utf-8",
    )
    skill_root.joinpath("SKILL.md").write_text(
        "---\nname: firmcli-test-skill\n---\n# Test skill\nTOKEN_NATIVE_SKILL\n",
        encoding="utf-8",
    )
    return skill_root


def test_codex_projection_uses_proven_codex_layout_and_metadata(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root)
    runtime_root = tmp_path / "runtime"
    working_directory = tmp_path / "work"

    projection = prepare_provider_native_skill_projection(
        provider="codex-cli",
        mode="auto",
        source_root=source_root,
        runtime_root=runtime_root,
        working_directory=working_directory,
    )

    assert projection.status == "available"
    assert projection.layout == ".codex/skills"
    assert projection.projection_root is not None
    assert projection.metadata_path is not None
    assert projection.projection_root == working_directory / ".codex" / "skills"
    assert (projection.projection_root / "firmcli-test-skill" / "SKILL.md").exists()
    assert projection.metadata_path == runtime_root / "firmcli-native-skills.json"
    assert projection.metadata_path.exists()
    assert "$firmcli-test-skill" in projection.prompt_text()
    assert 'load_skills(skill_ids=["firmcli-firmware-debug"])' in projection.prompt_text()
    assert "source/SKILL.md" in "\n".join(projection.source_hashes or {})
    assert "projected/SKILL.md" in "\n".join(projection.projected_hashes or {})


def test_claude_projection_sets_skill_allowlist(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root)

    projection = prepare_provider_native_skill_projection(
        provider="claude-cli",
        mode="auto",
        source_root=source_root,
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "work",
    )

    assert projection.status == "available"
    assert projection.layout == ".claude/skills"
    assert projection.claude_allowed_tools == ("Skill(firmcli-test-skill)",)
    assert "/firmcli-test-skill" in projection.prompt_text()


def test_provider_native_skills_off_disables_projection(tmp_path: Path) -> None:
    projection = prepare_provider_native_skill_projection(
        provider="codex-cli",
        mode="off",
        source_root=tmp_path / "missing",
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "work",
    )

    assert projection.status == "disabled"
    assert projection.prompt_text() == ""
    assert projection.projection_root is None


def test_api_provider_auto_is_fallback_only(tmp_path: Path) -> None:
    projection = prepare_provider_native_skill_projection(
        provider="openai-api",
        mode="auto",
        source_root=tmp_path / "missing",
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "work",
    )

    assert projection.status == "fallback-only"
    assert projection.projection_root is None
    assert "load_skills" in projection.prompt_text()


def test_api_provider_require_fails_early(tmp_path: Path) -> None:
    with pytest.raises(ProviderNativeSkillError, match="not available"):
        prepare_provider_native_skill_projection(
            provider="anthropic-api",
            mode="require",
            source_root=tmp_path / "missing",
            runtime_root=tmp_path / "runtime",
            working_directory=tmp_path / "work",
        )


def test_projection_refuses_to_overwrite_unmarked_existing_skill_dir(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root)
    existing = tmp_path / "work" / ".codex" / "skills" / "firmcli-test-skill"
    existing.mkdir(parents=True)
    existing.joinpath("SKILL.md").write_text("# User-owned skill\n", encoding="utf-8")

    with pytest.raises(ProviderNativeSkillError, match="Refusing to overwrite"):
        prepare_provider_native_skill_projection(
            provider="codex-cli",
            mode="auto",
            source_root=source_root,
            runtime_root=tmp_path / "runtime",
            working_directory=tmp_path / "work",
        )

    assert existing.joinpath("SKILL.md").read_text(encoding="utf-8") == "# User-owned skill\n"


def test_projection_replaces_previous_marked_firmcli_projection(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root)
    existing = tmp_path / "work" / ".codex" / "skills" / "firmcli-test-skill"
    existing.mkdir(parents=True)
    existing.joinpath(PROJECTION_MARKER_NAME).write_text("{}", encoding="utf-8")
    existing.joinpath("stale.txt").write_text("stale", encoding="utf-8")

    projection = prepare_provider_native_skill_projection(
        provider="codex-cli",
        mode="auto",
        source_root=source_root,
        runtime_root=tmp_path / "runtime",
        working_directory=tmp_path / "work",
    )

    assert projection.status == "available"
    assert not existing.joinpath("stale.txt").exists()
    assert existing.joinpath("SKILL.md").exists()
    assert existing.joinpath(PROJECTION_MARKER_NAME).exists()


def test_manifest_rejects_path_escape(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root, context_files=("SKILL.md", "../escape.md"))

    with pytest.raises(ProviderNativeSkillError, match="escapes"):
        load_provider_native_skill_manifests(source_root=source_root, provider="codex-cli")


def test_manifest_provider_variant_overrides_common(tmp_path: Path) -> None:
    source_root = tmp_path / "skills" / "provider_native"
    _write_provider_native_skill(source_root)
    variant_root = source_root / "codex" / "firmcli-test-skill"
    variant_root.mkdir(parents=True)
    variant_root.joinpath("skill.yaml").write_text(
        "\n".join(
            [
                "skill_id: firmcli-test-skill",
                "title: Codex Variant",
                "description: Codex-specific native provider skill.",
                "providers:",
                "  - codex-cli",
                "native_invocation:",
                "  codex-cli: $firmcli-test-skill",
                "fallback_skill_ids:",
                "  - firmcli-firmware-debug",
                "context_files:",
                "  - SKILL.md",
                "source_status: active",
                "",
            ]
        ),
        encoding="utf-8",
    )
    variant_root.joinpath("SKILL.md").write_text("# Codex variant\n", encoding="utf-8")

    manifests = load_provider_native_skill_manifests(
        source_root=source_root,
        provider="codex-cli",
    )

    assert len(manifests) == 1
    assert manifests[0].title == "Codex Variant"
