"""Model-native workflow skill loading for turnkey provider turns."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field, replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import yaml  # type: ignore[import-untyped]

DEFAULT_INIT_TIMEOUT_SECONDS = 30.0
MANIFEST_NAMES = ("skill.yaml", "skill.yml", "manifest.yaml", "manifest.yml")
FORBIDDEN_INIT_HARDWARE_IMPORTS = frozenset(
    {
        "cmsis_pack_manager",
        "hid",
        "jlink",
        "pylink",
        "pyocd",
        "serial",
        "usb",
    }
)
FORBIDDEN_INIT_HARDWARE_COMMANDS = frozenset(
    {
        "jlink",
        "jlinkexe",
        "nrfjprog",
        "openocd",
        "probe-rs",
        "pyocd",
        "st-flash",
        "st-info",
        "st-util",
    }
)


class ModelNativeSkillError(RuntimeError):
    """Raised when a model-native skill cannot be loaded."""


@dataclass(frozen=True)
class ModelNativeSkillManifest:
    skill_id: str
    title: str
    description: str
    root: Path
    depends_on: tuple[str, ...] = ()
    init_scripts: tuple[str, ...] = ()
    context_files: tuple[str, ...] = ("SKILL.md",)
    usable_paths: tuple[str, ...] = ()

    def to_record(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "title": self.title,
            "description": self.description,
            "root": str(self.root),
            "depends_on": list(self.depends_on),
            "init_scripts": list(self.init_scripts),
            "context_files": list(self.context_files),
            "usable_paths": list(self.usable_paths),
        }


@dataclass(frozen=True)
class ModelNativeSkillContextFile:
    relative_path: str
    absolute_path: str
    sha256: str
    body: str

    def to_record(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "sha256": self.sha256,
            "body_length": len(self.body),
        }


@dataclass(frozen=True)
class ModelNativeSkillInitResult:
    skill_id: str
    script: str
    cwd: str
    timeout_seconds: float
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str

    def to_record(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "script": self.script,
            "cwd": self.cwd,
            "timeout_seconds": self.timeout_seconds,
            "exit_code": self.exit_code,
            "duration_seconds": self.duration_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class LoadedModelNativeSkill:
    manifest: ModelNativeSkillManifest
    runtime_path: str
    context_files: tuple[ModelNativeSkillContextFile, ...]
    init_results: tuple[ModelNativeSkillInitResult, ...] = ()
    initialized: bool = True
    context_injected: bool = True

    def to_record(self) -> dict[str, object]:
        return {
            "manifest": self.manifest.to_record(),
            "runtime_path": self.runtime_path,
            "context_files": [item.to_record() for item in self.context_files],
            "init_results": [item.to_record() for item in self.init_results],
            "initialized": self.initialized,
            "context_injected": self.context_injected,
        }


@dataclass(frozen=True)
class ModelNativeSkillSessionState:
    requested_skill_ids: tuple[str, ...] = ()
    resolved_skill_ids: tuple[str, ...] = ()
    init_order: tuple[str, ...] = ()
    initialized_skill_ids: tuple[str, ...] = ()
    context_injected_skill_ids: tuple[str, ...] = ()
    exposed_runtime_paths: dict[str, str] = field(default_factory=dict)
    init_results: tuple[ModelNativeSkillInitResult, ...] = ()
    failures: tuple[str, ...] = ()
    loaded_skills: dict[str, LoadedModelNativeSkill] = field(default_factory=dict)

    def to_record(self) -> dict[str, object]:
        return {
            "requested_skill_ids": list(self.requested_skill_ids),
            "resolved_skill_ids": list(self.resolved_skill_ids),
            "init_order": list(self.init_order),
            "initialized_skill_ids": list(self.initialized_skill_ids),
            "context_injected_skill_ids": list(self.context_injected_skill_ids),
            "exposed_runtime_paths": dict(self.exposed_runtime_paths),
            "init_results": [item.to_record() for item in self.init_results],
            "failures": list(self.failures),
            "loaded_skills": {
                skill_id: skill.to_record()
                for skill_id, skill in sorted(self.loaded_skills.items())
            },
        }

    def with_failure(self, failure: str) -> "ModelNativeSkillSessionState":
        return replace(self, failures=(*self.failures, failure))


@dataclass(frozen=True)
class ModelNativeSkillLoadResult:
    requested_skill_ids: tuple[str, ...]
    resolved_skill_ids: tuple[str, ...]
    newly_loaded_skill_ids: tuple[str, ...]
    already_loaded_skill_ids: tuple[str, ...]
    init_order: tuple[str, ...]
    runtime_paths: dict[str, str]
    init_results: tuple[ModelNativeSkillInitResult, ...]
    state: ModelNativeSkillSessionState

    def to_record(self) -> dict[str, object]:
        return {
            "requested_skill_ids": list(self.requested_skill_ids),
            "resolved_skill_ids": list(self.resolved_skill_ids),
            "newly_loaded_skill_ids": list(self.newly_loaded_skill_ids),
            "already_loaded_skill_ids": list(self.already_loaded_skill_ids),
            "init_order": list(self.init_order),
            "runtime_paths": dict(self.runtime_paths),
            "init_results": [item.to_record() for item in self.init_results],
        }

    def render_result_text(self) -> str:
        loaded = ", ".join(self.newly_loaded_skill_ids) or "(none)"
        already = ", ".join(self.already_loaded_skill_ids) or "(none)"
        resolved = ", ".join(self.resolved_skill_ids) or "(none)"
        return (
            "Loaded model-native skills.\n"
            f"requested={list(self.requested_skill_ids)}\n"
            f"resolved_order={resolved}\n"
            f"newly_loaded={loaded}\n"
            f"already_loaded={already}\n"
            f"runtime_paths={json.dumps(self.runtime_paths, sort_keys=True)}"
        )


class ModelNativeSkillRegistry:
    """Loads folder-based model-native workflow skill manifests."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def load_manifest(self, skill_id: str) -> ModelNativeSkillManifest:
        root = self.root / skill_id
        if not root.is_dir():
            raise ModelNativeSkillError(f"Unknown model-native skill: {skill_id}")
        manifest_path = _find_manifest_path(root)
        if manifest_path is None:
            return _manifest_from_skill_md(root, skill_id)
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ModelNativeSkillError(f"Skill manifest is not an object: {manifest_path}")
        manifest = _manifest_from_mapping(root, raw)
        if manifest.skill_id != skill_id:
            raise ModelNativeSkillError(
                f"Skill manifest id {manifest.skill_id!r} does not match requested skill "
                f"{skill_id!r}: {manifest_path}"
            )
        return manifest

    def resolve_closure(self, skill_ids: tuple[str, ...]) -> tuple[ModelNativeSkillManifest, ...]:
        ordered: list[ModelNativeSkillManifest] = []
        visited: set[str] = set()
        visiting: list[str] = []

        def visit(skill_id: str) -> None:
            if skill_id in visited:
                return
            if skill_id in visiting:
                start = visiting.index(skill_id)
                cycle = (*visiting[start:], skill_id)
                raise ModelNativeSkillError("Skill dependency cycle: " + " -> ".join(cycle))
            visiting.append(skill_id)
            manifest = self.load_manifest(skill_id)
            for dependency in manifest.depends_on:
                visit(dependency)
            visiting.pop()
            visited.add(skill_id)
            ordered.append(manifest)

        for skill_id in _normalize_skill_ids(skill_ids):
            visit(skill_id)
        return tuple(ordered)

    def load_skills(
        self,
        *,
        skill_ids: tuple[str, ...],
        session_state: ModelNativeSkillSessionState,
        runtime_root: Path,
        repo_root: Path,
        timeout_seconds: float = DEFAULT_INIT_TIMEOUT_SECONDS,
    ) -> ModelNativeSkillLoadResult:
        requested = _normalize_skill_ids(skill_ids)
        manifests = self.resolve_closure(requested)
        resolved_ids = tuple(manifest.skill_id for manifest in manifests)
        already_loaded = tuple(
            skill_id for skill_id in resolved_ids if skill_id in session_state.loaded_skills
        )
        newly_loaded: list[str] = []
        loaded = dict(session_state.loaded_skills)
        runtime_paths = dict(session_state.exposed_runtime_paths)
        init_results = list(session_state.init_results)
        current_init_results: list[ModelNativeSkillInitResult] = []

        skills_root = runtime_root / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)
        for manifest in manifests:
            if manifest.skill_id in loaded:
                continue
            skill_runtime_root = skills_root / manifest.skill_id
            skill_runtime_root.mkdir(parents=True, exist_ok=True)
            _expose_usable_paths(manifest, skill_runtime_root)
            results = tuple(
                _run_init_script(
                    manifest=manifest,
                    script=script,
                    runtime_root=skill_runtime_root,
                    repo_root=repo_root,
                    timeout_seconds=timeout_seconds,
                )
                for script in manifest.init_scripts
            )
            context_files = _load_context_files(manifest)
            loaded_skill = LoadedModelNativeSkill(
                manifest=manifest,
                runtime_path=str(skill_runtime_root),
                context_files=context_files,
                init_results=results,
            )
            loaded[manifest.skill_id] = loaded_skill
            runtime_paths[manifest.skill_id] = str(skill_runtime_root)
            newly_loaded.append(manifest.skill_id)
            current_init_results.extend(results)
            init_results.extend(results)

        initialized_ids = tuple(skill_id for skill_id in resolved_ids if skill_id in loaded)
        context_injected_ids = initialized_ids
        next_state = ModelNativeSkillSessionState(
            requested_skill_ids=_dedupe_preserving_order(
                (*session_state.requested_skill_ids, *requested)
            ),
            resolved_skill_ids=_dedupe_preserving_order(
                (*session_state.resolved_skill_ids, *resolved_ids)
            ),
            init_order=_dedupe_preserving_order((*session_state.init_order, *newly_loaded)),
            initialized_skill_ids=_dedupe_preserving_order(
                (*session_state.initialized_skill_ids, *initialized_ids)
            ),
            context_injected_skill_ids=_dedupe_preserving_order(
                (*session_state.context_injected_skill_ids, *context_injected_ids)
            ),
            exposed_runtime_paths=runtime_paths,
            init_results=tuple(init_results),
            failures=session_state.failures,
            loaded_skills=loaded,
        )
        return ModelNativeSkillLoadResult(
            requested_skill_ids=requested,
            resolved_skill_ids=resolved_ids,
            newly_loaded_skill_ids=tuple(newly_loaded),
            already_loaded_skill_ids=already_loaded,
            init_order=tuple(newly_loaded),
            runtime_paths={skill_id: runtime_paths[skill_id] for skill_id in resolved_ids},
            init_results=tuple(current_init_results),
            state=next_state,
        )


def render_model_native_skill_context(state: ModelNativeSkillSessionState) -> str:
    if not state.loaded_skills:
        return "No model-native workflow skills loaded."
    blocks = [
        "Loaded model-native workflow skills:",
        "loaded_skill_ids=" + ", ".join(sorted(state.loaded_skills)),
        "init_order=" + ", ".join(state.init_order),
    ]
    for skill_id in state.resolved_skill_ids:
        skill = state.loaded_skills.get(skill_id)
        if skill is None:
            continue
        blocks.append("")
        blocks.append(f"## {skill.manifest.skill_id}: {skill.manifest.title}")
        blocks.append(f"description: {skill.manifest.description}")
        blocks.append(
            "depends_on: "
            + (", ".join(skill.manifest.depends_on) if skill.manifest.depends_on else "(none)")
        )
        blocks.append(f"usable_runtime_path: {skill.runtime_path}")
        if skill.manifest.usable_paths:
            blocks.append("usable_paths: " + ", ".join(skill.manifest.usable_paths))
        if skill.init_results:
            summaries = [
                f"{result.script}: exit_code={result.exit_code}" for result in skill.init_results
            ]
            blocks.append("init_results: " + "; ".join(summaries))
        for context_file in skill.context_files:
            blocks.append(f"### {context_file.relative_path} sha256={context_file.sha256}")
            blocks.append(context_file.body.strip())
    return "\n".join(blocks)


def _find_manifest_path(root: Path) -> Path | None:
    for name in MANIFEST_NAMES:
        path = root / name
        if path.is_file():
            return path
    return None


def _manifest_from_mapping(root: Path, raw: dict[object, object]) -> ModelNativeSkillManifest:
    skill_id = _required_str(raw, "skill_id")
    return ModelNativeSkillManifest(
        skill_id=skill_id,
        title=_optional_str(raw, "title", skill_id),
        description=_optional_str(raw, "description", ""),
        root=root,
        depends_on=_string_tuple(raw.get("depends_on")),
        init_scripts=_string_tuple(raw.get("init_scripts")),
        context_files=_string_tuple(raw.get("context_files"), default=("SKILL.md",)),
        usable_paths=_string_tuple(raw.get("usable_paths")),
    )


def _manifest_from_skill_md(root: Path, skill_id: str) -> ModelNativeSkillManifest:
    path = root / "SKILL.md"
    if not path.is_file():
        raise ModelNativeSkillError(f"Skill {skill_id!r} has no manifest or SKILL.md")
    return ModelNativeSkillManifest(
        skill_id=skill_id,
        title=skill_id.replace("-", " ").title(),
        description="",
        root=root,
        context_files=("SKILL.md",),
    )


def _required_str(raw: dict[object, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ModelNativeSkillError(f"Skill manifest missing non-empty {key!r}")
    return value.strip()


def _optional_str(raw: dict[object, object], key: str, default: str) -> str:
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ModelNativeSkillError(f"Skill manifest field {key!r} must be a string")
    return value.strip()


def _string_tuple(value: object, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        raise ModelNativeSkillError("Skill manifest list fields must be arrays")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ModelNativeSkillError("Skill manifest list items must be non-empty strings")
        items.append(item.strip())
    return tuple(items)


def _normalize_skill_ids(skill_ids: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(skill_id.strip() for skill_id in skill_ids)
    if not normalized or any(not skill_id for skill_id in normalized):
        raise ModelNativeSkillError("skill_ids must contain at least one non-empty skill ID")
    return _dedupe_preserving_order(normalized)


def _dedupe_preserving_order(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return tuple(ordered)


def _safe_child_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ModelNativeSkillError(f"Skill path escapes skill root: {relative_path}")
    return candidate


def _load_context_files(
    manifest: ModelNativeSkillManifest,
) -> tuple[ModelNativeSkillContextFile, ...]:
    files: list[ModelNativeSkillContextFile] = []
    for relative_path in manifest.context_files:
        path = _safe_child_path(manifest.root, relative_path)
        if not path.is_file():
            raise ModelNativeSkillError(
                f"Context file {relative_path!r} missing for skill {manifest.skill_id!r}"
            )
        body = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        files.append(
            ModelNativeSkillContextFile(
                relative_path=relative_path,
                absolute_path=str(path),
                sha256=digest,
                body=body,
            )
        )
    return tuple(files)


def _expose_usable_paths(manifest: ModelNativeSkillManifest, runtime_root: Path) -> None:
    for relative_path in manifest.usable_paths:
        source = _safe_child_path(manifest.root, relative_path)
        if not source.exists():
            raise ModelNativeSkillError(
                f"Usable path {relative_path!r} missing for skill {manifest.skill_id!r}"
            )
        destination = runtime_root / relative_path
        if source.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _run_init_script(
    *,
    manifest: ModelNativeSkillManifest,
    script: str,
    runtime_root: Path,
    repo_root: Path,
    timeout_seconds: float,
) -> ModelNativeSkillInitResult:
    script_path = _safe_child_path(manifest.root, script)
    if not script_path.is_file():
        raise ModelNativeSkillError(
            f"Init script {script!r} missing for skill {manifest.skill_id!r}"
        )
    _validate_init_script_policy(manifest, script, script_path)
    command = (
        [sys.executable, str(script_path)] if script_path.suffix == ".py" else [str(script_path)]
    )
    env = {
        **dict(os.environ),
        "FIRMCLI_REPO_ROOT": str(repo_root),
        "FIRMCLI_SKILL_SOURCE_DIR": str(manifest.root),
        "FIRMCLI_SKILL_RUNTIME_DIR": str(runtime_root),
    }
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=runtime_root,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        raise ModelNativeSkillError(
            f"Init script timed out for skill {manifest.skill_id!r}: {script}; "
            f"stdout={stdout[:200]!r}; stderr={stderr[:200]!r}"
        ) from exc
    duration = time.perf_counter() - started
    result = ModelNativeSkillInitResult(
        skill_id=manifest.skill_id,
        script=script,
        cwd=str(runtime_root),
        timeout_seconds=timeout_seconds,
        exit_code=completed.returncode,
        duration_seconds=duration,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if completed.returncode != 0:
        raise ModelNativeSkillError(
            f"Init script failed for skill {manifest.skill_id!r}: "
            f"{script} exit_code={completed.returncode}"
        )
    return result


def _validate_init_script_policy(
    manifest: ModelNativeSkillManifest,
    script: str,
    script_path: Path,
) -> None:
    try:
        source = script_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ModelNativeSkillError(
            f"Init script must be UTF-8 text for policy validation: {manifest.skill_id!r} {script}"
        ) from exc
    if script_path.suffix == ".py":
        _validate_python_init_script_policy(manifest, script, script_path, source)
        return
    lowered = source.lower()
    for command in FORBIDDEN_INIT_HARDWARE_COMMANDS:
        if command in lowered:
            raise ModelNativeSkillError(
                f"Init script uses direct hardware/probe command {command!r}; "
                f"skill={manifest.skill_id!r} script={script}"
            )


def _validate_python_init_script_policy(
    manifest: ModelNativeSkillManifest,
    script: str,
    script_path: Path,
    source: str,
) -> None:
    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError as exc:
        raise ModelNativeSkillError(
            f"Init script has invalid Python syntax: {manifest.skill_id!r} {script}"
        ) from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _raise_if_forbidden_init_import(manifest, script, alias.name)
            continue
        if isinstance(node, ast.ImportFrom) and node.module:
            _raise_if_forbidden_init_import(manifest, script, node.module)
            continue
        if isinstance(node, ast.Call) and _is_subprocess_call(node.func):
            command = _literal_command_name(node)
            if command is not None:
                _raise_if_forbidden_init_command(manifest, script, command)


def _raise_if_forbidden_init_import(
    manifest: ModelNativeSkillManifest,
    script: str,
    module_name: str,
) -> None:
    root_module = module_name.split(".", 1)[0].lower()
    if root_module in FORBIDDEN_INIT_HARDWARE_IMPORTS:
        raise ModelNativeSkillError(
            f"Init script imports direct hardware/probe module {root_module!r}; "
            f"skill={manifest.skill_id!r} script={script}"
        )


def _raise_if_forbidden_init_command(
    manifest: ModelNativeSkillManifest,
    script: str,
    command_name: str,
) -> None:
    executable = Path(command_name).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]
    if executable in FORBIDDEN_INIT_HARDWARE_COMMANDS:
        raise ModelNativeSkillError(
            f"Init script uses direct hardware/probe command {executable!r}; "
            f"skill={manifest.skill_id!r} script={script}"
        )


def _is_subprocess_call(function: ast.expr) -> bool:
    if not isinstance(function, ast.Attribute):
        return False
    if function.attr not in {"run", "call", "check_call", "check_output", "Popen"}:
        return False
    return isinstance(function.value, ast.Name) and function.value.id == "subprocess"


def _literal_command_name(call: ast.Call) -> str | None:
    if not call.args:
        return None
    first_arg = call.args[0]
    if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
        return first_arg.value.split()[0] if first_arg.value.split() else None
    if isinstance(first_arg, ast.List | ast.Tuple) and first_arg.elts:
        first_element = first_arg.elts[0]
        if isinstance(first_element, ast.Constant) and isinstance(first_element.value, str):
            return first_element.value
    return None
