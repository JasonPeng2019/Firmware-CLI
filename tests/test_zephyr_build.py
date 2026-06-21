from __future__ import annotations

from pathlib import Path

from pyocd_debug_mcp import zephyr_build


def test_workspace_candidates_prefer_explicit_env_and_common_locations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    explicit = tmp_path / "explicit-workspace"
    env_workspace = tmp_path / "env-workspace"
    home = tmp_path / "home"
    managed = tmp_path / "managed-workspace"
    (explicit / "zephyr").mkdir(parents=True)
    (env_workspace / "zephyr").mkdir(parents=True)
    (home / "zephyrproject" / "zephyr").mkdir(parents=True)
    monkeypatch.setenv("ZEPHYR_WORKSPACE_DIR", str(env_workspace))
    monkeypatch.setattr(zephyr_build.Path, "home", staticmethod(lambda: home))

    candidates = zephyr_build._iter_zephyr_workspace_candidates(
        explicit_workspace_dir=explicit,
        managed_workspace_dir=managed,
    )

    assert candidates[0].path == explicit.resolve()
    assert candidates[0].source == "--workspace-dir"
    assert any(candidate.path == env_workspace.resolve() for candidate in candidates)
    assert any(candidate.path == (home / "zephyrproject").resolve() for candidate in candidates)
    assert candidates[-1].path == managed.resolve()


def test_sdk_candidates_include_workspace_adjacent_ncs_toolchain(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "ncs" / "v3.3.1"
    managed = tmp_path / "managed-sdk"
    toolchain_sdk = workspace.parent / "toolchains" / "1234" / "opt" / "zephyr-sdk"
    toolchain_sdk.mkdir(parents=True)
    (toolchain_sdk / "sdk_version").write_text("0.17.4\n", encoding="utf-8")
    monkeypatch.delenv("ZEPHYR_SDK_INSTALL_DIR", raising=False)

    candidates = zephyr_build._iter_sdk_candidates(
        explicit_sdk_dir=None,
        managed_sdk_dir=managed,
        workspace_dir=workspace,
    )

    assert candidates[0].path == managed.resolve()
    assert any(candidate.path == toolchain_sdk.resolve() for candidate in candidates)


def test_clean_build_dir_preserves_gitkeep_and_gitignore(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / ".gitkeep").write_text("", encoding="utf-8")
    (build_dir / ".gitignore").write_text("*\n", encoding="utf-8")
    (build_dir / "firmware.elf").write_text("old", encoding="utf-8")
    (build_dir / "temp").mkdir()
    (build_dir / "temp" / "nested.txt").write_text("nested", encoding="utf-8")

    zephyr_build._clean_build_dir(build_dir)

    assert (build_dir / ".gitkeep").exists()
    assert (build_dir / ".gitignore").exists()
    assert not (build_dir / "firmware.elf").exists()
    assert not (build_dir / "temp").exists()


def test_copy_artifacts_preserves_live_build_tree_when_output_dir_matches_work_dir(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    zephyr_dir = build_dir / "zephyr"
    zephyr_dir.mkdir(parents=True)
    elf_contents = "elf"
    hex_contents = "hex"
    (zephyr_dir / "zephyr.elf").write_text(elf_contents, encoding="utf-8")
    (zephyr_dir / "zephyr.hex").write_text(hex_contents, encoding="utf-8")
    (build_dir / "build.ninja").write_text("ninja", encoding="utf-8")

    zephyr_build._copy_artifacts(build_dir, build_dir, app_dir_name="app")

    assert (build_dir / "build.ninja").read_text(encoding="utf-8") == "ninja"
    assert (zephyr_dir / "zephyr.elf").read_text(encoding="utf-8") == elf_contents
    assert (build_dir / "firmware.elf").read_text(encoding="utf-8") == elf_contents
    assert (build_dir / "firmware.hex").read_text(encoding="utf-8") == hex_contents


def test_copy_artifacts_resolves_sysbuild_app_subdir(tmp_path: Path) -> None:
    build_dir = tmp_path / "build"
    app_zephyr_dir = build_dir / "src" / "zephyr"
    app_zephyr_dir.mkdir(parents=True)
    (app_zephyr_dir / "zephyr.elf").write_text("elf", encoding="utf-8")
    (app_zephyr_dir / "zephyr.hex").write_text("hex", encoding="utf-8")

    zephyr_build._copy_artifacts(build_dir, build_dir, app_dir_name="src")

    assert (build_dir / "firmware.elf").read_text(encoding="utf-8") == "elf"
    assert (build_dir / "firmware.hex").read_text(encoding="utf-8") == "hex"


def test_build_parser_defaults_to_incremental_pristine_mode() -> None:
    args = zephyr_build.build_parser().parse_args(
        [
            "--app-dir",
            "app",
            "--build-dir",
            "build",
            "--board",
            "nucleo_l476rg",
        ]
    )

    assert args.pristine == "auto"
