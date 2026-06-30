from __future__ import annotations

from pathlib import Path

import pytest

from pyocd_debug_mcp.brain.model_native_skills import (
    ModelNativeSkillError,
    ModelNativeSkillRegistry,
    ModelNativeSkillSessionState,
    render_model_native_skill_context,
)


def _write_skill(
    root: Path,
    skill_id: str,
    *,
    depends_on: tuple[str, ...] = (),
    init: bool = False,
    order_file: Path | None = None,
    usable: bool = False,
) -> None:
    skill_root = root / skill_id
    skill_root.mkdir(parents=True)
    init_scripts: list[str] = []
    if init:
        assert order_file is not None
        scripts = skill_root / "scripts"
        scripts.mkdir()
        (scripts / "init.py").write_text(
            "\n".join(
                [
                    "from pathlib import Path",
                    f"path = Path({str(order_file)!r})",
                    "existing = path.read_text(encoding='utf-8') if path.exists() else ''",
                    f"path.write_text(existing + {skill_id + chr(10)!r}, encoding='utf-8')",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        init_scripts.append("scripts/init.py")
    usable_paths: list[str] = []
    if usable:
        assets = skill_root / "assets"
        assets.mkdir()
        (assets / "helper.txt").write_text(f"{skill_id} helper\n", encoding="utf-8")
        usable_paths.append("assets/")
    depends = "[" + ", ".join(depends_on) + "]"
    init_value = "[" + ", ".join(init_scripts) + "]"
    usable_value = "[" + ", ".join(usable_paths) + "]"
    (skill_root / "skill.yaml").write_text(
        "\n".join(
            [
                f"skill_id: {skill_id}",
                f"title: {skill_id}",
                f"description: {skill_id} description",
                f"depends_on: {depends}",
                f"init_scripts: {init_value}",
                "context_files: [SKILL.md]",
                f"usable_paths: {usable_value}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (skill_root / "SKILL.md").write_text(f"{skill_id} instructions\n", encoding="utf-8")


def test_model_native_skills_resolve_transitive_deps_and_init_post_order(
    tmp_path: Path,
) -> None:
    skill_root = tmp_path / "skills"
    order_file = tmp_path / "init-order.txt"
    _write_skill(skill_root, "workflow-core", init=True, order_file=order_file, usable=True)
    _write_skill(
        skill_root,
        "python-change",
        depends_on=("workflow-core",),
        init=True,
        order_file=order_file,
    )
    _write_skill(
        skill_root,
        "fix-bug",
        depends_on=("workflow-core", "python-change"),
        init=True,
        order_file=order_file,
    )
    _write_skill(
        skill_root,
        "wrapper",
        depends_on=("fix-bug",),
        init=True,
        order_file=order_file,
    )
    registry = ModelNativeSkillRegistry(skill_root)

    result = registry.load_skills(
        skill_ids=("wrapper",),
        session_state=ModelNativeSkillSessionState(),
        runtime_root=tmp_path / "runtime",
        repo_root=tmp_path,
    )

    assert result.resolved_skill_ids == (
        "workflow-core",
        "python-change",
        "fix-bug",
        "wrapper",
    )
    assert result.newly_loaded_skill_ids == result.resolved_skill_ids
    assert order_file.read_text(encoding="utf-8").splitlines() == [
        "workflow-core",
        "python-change",
        "fix-bug",
        "wrapper",
    ]
    assert len(result.init_results) == 4
    assert (Path(result.runtime_paths["workflow-core"]) / "assets" / "helper.txt").exists()
    context = render_model_native_skill_context(result.state)
    assert "workflow-core instructions" in context
    assert "wrapper instructions" in context

    repeat = registry.load_skills(
        skill_ids=("wrapper", "fix-bug"),
        session_state=result.state,
        runtime_root=tmp_path / "runtime",
        repo_root=tmp_path,
    )

    assert repeat.newly_loaded_skill_ids == ()
    assert repeat.already_loaded_skill_ids == result.resolved_skill_ids
    assert repeat.init_results == ()
    assert order_file.read_text(encoding="utf-8").splitlines() == [
        "workflow-core",
        "python-change",
        "fix-bug",
        "wrapper",
    ]


def test_model_native_skill_cycles_fail_with_full_path(tmp_path: Path) -> None:
    skill_root = tmp_path / "skills"
    _write_skill(skill_root, "a", depends_on=("b",))
    _write_skill(skill_root, "b", depends_on=("c",))
    _write_skill(skill_root, "c", depends_on=("a",))
    registry = ModelNativeSkillRegistry(skill_root)

    with pytest.raises(ModelNativeSkillError, match="a -> b -> c -> a"):
        registry.resolve_closure(("a",))


def test_model_native_skill_manifest_id_must_match_requested_folder(tmp_path: Path) -> None:
    skill_root = tmp_path / "skills"
    _write_skill(skill_root, "actual")
    manifest = skill_root / "actual" / "skill.yaml"
    manifest.write_text(
        "\n".join(
            [
                "skill_id: spoofed",
                "title: spoofed",
                "description: mismatched manifest",
                "depends_on: []",
                "init_scripts: []",
                "context_files: [SKILL.md]",
                "usable_paths: []",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    registry = ModelNativeSkillRegistry(skill_root)

    with pytest.raises(ModelNativeSkillError, match="does not match requested skill"):
        registry.load_manifest("actual")


def test_model_native_skill_failed_load_can_be_repaired_in_runtime_copy(
    tmp_path: Path,
) -> None:
    skill_root = tmp_path / "skills"
    _write_skill(skill_root, "repairable")
    manifest = skill_root / "repairable" / "skill.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "context_files: [SKILL.md]", "context_files: [missing.md]"
        ),
        encoding="utf-8",
    )
    registry = ModelNativeSkillRegistry(skill_root)
    runtime_root = tmp_path / "runtime"

    with pytest.raises(ModelNativeSkillError) as exc_info:
        registry.load_skills(
            skill_ids=("repairable",),
            session_state=ModelNativeSkillSessionState(),
            runtime_root=runtime_root,
            repo_root=tmp_path,
        )

    failure = exc_info.value.to_failure(requested_skill_ids=("repairable",))
    assert failure.category == "missing_context_file"
    runtime_skill = runtime_root / "skills" / "repairable"
    assert runtime_skill.exists()
    (runtime_skill / "missing.md").write_text("runtime repair body\n", encoding="utf-8")
    assert not (skill_root / "repairable" / "missing.md").exists()

    result = registry.load_skills(
        skill_ids=("repairable",),
        session_state=ModelNativeSkillSessionState(),
        runtime_root=runtime_root,
        repo_root=tmp_path,
    )

    context = render_model_native_skill_context(result.state)
    assert "runtime repair body" in context
    assert result.state.loaded_skills["repairable"].source_path == str(skill_root / "repairable")


def test_model_native_skill_init_rejects_direct_hardware_imports(tmp_path: Path) -> None:
    skill_root = tmp_path / "skills"
    _write_skill(skill_root, "bad-init", init=False)
    scripts = skill_root / "bad-init" / "scripts"
    scripts.mkdir()
    (scripts / "init.py").write_text("import serial\n", encoding="utf-8")
    manifest = skill_root / "bad-init" / "skill.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "init_scripts: []", "init_scripts: [scripts/init.py]"
        ),
        encoding="utf-8",
    )
    registry = ModelNativeSkillRegistry(skill_root)

    with pytest.raises(ModelNativeSkillError, match="direct hardware/probe module"):
        registry.load_skills(
            skill_ids=("bad-init",),
            session_state=ModelNativeSkillSessionState(),
            runtime_root=tmp_path / "runtime",
            repo_root=tmp_path,
        )


def test_model_native_skill_init_rejects_direct_hardware_commands(tmp_path: Path) -> None:
    skill_root = tmp_path / "skills"
    _write_skill(skill_root, "bad-init", init=False)
    scripts = skill_root / "bad-init" / "scripts"
    scripts.mkdir()
    (scripts / "init.py").write_text(
        "import subprocess\nsubprocess.run(['pyocd', 'list'], check=False)\n",
        encoding="utf-8",
    )
    manifest = skill_root / "bad-init" / "skill.yaml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "init_scripts: []", "init_scripts: [scripts/init.py]"
        ),
        encoding="utf-8",
    )
    registry = ModelNativeSkillRegistry(skill_root)

    with pytest.raises(ModelNativeSkillError, match="direct hardware/probe command"):
        registry.load_skills(
            skill_ids=("bad-init",),
            session_state=ModelNativeSkillSessionState(),
            runtime_root=tmp_path / "runtime",
            repo_root=tmp_path,
        )
