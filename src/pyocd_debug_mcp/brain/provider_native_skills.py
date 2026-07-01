"""Provider-native skill projection for CLI-backed turnkey providers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import time
from typing import Literal, cast

import yaml  # type: ignore[import-untyped]

ProviderNativeSkillMode = Literal["off", "auto", "require"]
ProviderNativeSkillStatus = Literal[
    "disabled",
    "available",
    "fallback-only",
    "unavailable",
]
ProviderNativeSkillProvider = Literal["codex-cli", "claude-cli"]

MANIFEST_NAMES = ("skill.yaml", "skill.yml", "manifest.yaml", "manifest.yml")
SUPPORTED_NATIVE_PROVIDERS = frozenset({"codex-cli", "claude-cli"})
PROVIDER_VARIANT_DIRS = {
    "codex-cli": "codex",
    "claude-cli": "claude",
}
PROVIDER_LAYOUT_ROOTS = {
    "codex-cli": Path(".codex") / "skills",  # VENDOR-FIXED, phase-0-proven local CLI
    "claude-cli": Path(".claude") / "skills",  # VENDOR-FIXED, phase-0-proven with Skill(...)
}
PROVIDER_INVOCATION_STYLES = {
    "codex-cli": "$skill-id or explicit skill request",
    "claude-cli": "/skill-id with Skill(skill-id) allowed",
}
PROJECTION_MARKER_NAME = ".firmcli-provider-native-projection.json"


class ProviderNativeSkillError(RuntimeError):
    """Raised when provider-native skill projection cannot satisfy the requested mode."""


@dataclass(frozen=True)
class ProviderNativeSkillManifest:
    skill_id: str
    title: str
    description: str
    providers: tuple[ProviderNativeSkillProvider, ...]
    native_invocation: dict[str, str]
    fallback_skill_ids: tuple[str, ...]
    root: Path
    depends_on: tuple[str, ...] = ()
    context_files: tuple[str, ...] = ("SKILL.md",)
    usable_paths: tuple[str, ...] = ()
    requires_governed_actions: tuple[str, ...] = ()
    source_status: str = "active"

    def invocation_for(self, provider: str) -> str:
        return self.native_invocation.get(provider) or self.native_invocation.get("*") or ""

    def to_record(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "title": self.title,
            "description": self.description,
            "providers": list(self.providers),
            "native_invocation": dict(self.native_invocation),
            "fallback_skill_ids": list(self.fallback_skill_ids),
            "root": str(self.root),
            "depends_on": list(self.depends_on),
            "context_files": list(self.context_files),
            "usable_paths": list(self.usable_paths),
            "requires_governed_actions": list(self.requires_governed_actions),
            "source_status": self.source_status,
        }


@dataclass(frozen=True)
class ProviderNativeSkillProjection:
    provider: str
    mode: ProviderNativeSkillMode
    status: ProviderNativeSkillStatus
    source_root: Path
    runtime_root: Path
    working_directory: Path
    projection_root: Path | None
    metadata_path: Path | None
    layout: str | None
    invocation_style: str | None
    probe_status: str
    probe_details: dict[str, object]
    manifests: tuple[ProviderNativeSkillManifest, ...] = ()
    source_hashes: dict[str, str] | None = None
    projected_hashes: dict[str, str] | None = None

    @property
    def enabled(self) -> bool:
        return self.status == "available" and bool(self.manifests)

    @property
    def claude_allowed_tools(self) -> tuple[str, ...]:
        if self.provider != "claude-cli" or not self.enabled:
            return ()
        return tuple(f"Skill({manifest.skill_id})" for manifest in self.manifests)

    def prompt_text(self) -> str:
        if self.mode == "off" or self.status == "disabled":
            return ""
        if not self.manifests:
            if self.status == "fallback-only":
                return (
                    "Provider-native FirmCLI skills unavailable for this provider.\n"
                    "Use FirmCLI load_skills(skill_ids=[...]) when workflow skill context is needed."
                )
            return ""
        lines = ["Provider-native FirmCLI skills available:"]
        for manifest in self.manifests:
            fallback = ", ".join(f'"{skill_id}"' for skill_id in manifest.fallback_skill_ids)
            fallback_text = (
                f"load_skills(skill_ids=[{fallback}])"
                if fallback
                else "load_skills with the closest listed FirmCLI model-native skill"
            )
            invocation = manifest.invocation_for(self.provider) or "(native provider match)"
            lines.extend(
                [
                    f"- {manifest.skill_id}: {manifest.description}",
                    f"  Preferred native invocation for this provider: {invocation}",
                    f"  Fallback if native invocation fails or is uncertain: {fallback_text}.",
                ]
            )
        lines.extend(
            [
                "",
                "Rules:",
                "- Prefer provider-native skill invocation for these listed skills when available.",
                "- Do not invent skill names not listed here.",
                "- Do not use provider-native skills to execute board actions directly.",
                "- Native skills guide provider-side host reasoning only; every turn still ends with one FirmCLI TurnDecision.",
                "- If native skill handling fails, request FirmCLI load_skills as fallback.",
            ]
        )
        return "\n".join(lines)

    def to_record(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "mode": self.mode,
            "status": self.status,
            "source_root": str(self.source_root),
            "runtime_root": str(self.runtime_root),
            "working_directory": str(self.working_directory),
            "projection_root": str(self.projection_root) if self.projection_root else None,
            "metadata_path": str(self.metadata_path) if self.metadata_path else None,
            "layout": self.layout,
            "invocation_style": self.invocation_style,
            "probe_status": self.probe_status,
            "probe_details": dict(self.probe_details),
            "projected_skill_ids": [manifest.skill_id for manifest in self.manifests],
            "skills": [manifest.to_record() for manifest in self.manifests],
            "source_hashes": dict(self.source_hashes or {}),
            "projected_hashes": dict(self.projected_hashes or {}),
            "prompt_context_hash": _sha256_text(self.prompt_text()),
            "prompt_context_length": len(self.prompt_text()),
            "claude_allowed_tools": list(self.claude_allowed_tools),
        }


def cast_provider_native_skill_mode(raw_mode: str) -> ProviderNativeSkillMode:
    candidate = raw_mode.strip().lower()
    if candidate in {"off", "auto", "require"}:
        return cast(ProviderNativeSkillMode, candidate)
    raise ProviderNativeSkillError("Unsupported native skill mode. Use one of: off, auto, require.")


def prepare_provider_native_skill_projection(
    *,
    provider: str,
    mode: ProviderNativeSkillMode,
    source_root: Path,
    runtime_root: Path,
    working_directory: Path,
) -> ProviderNativeSkillProjection:
    source_root = source_root.expanduser().resolve()
    runtime_root = runtime_root.expanduser().resolve()
    working_directory = working_directory.expanduser().resolve()
    if mode == "off":
        return ProviderNativeSkillProjection(
            provider=provider,
            mode=mode,
            status="disabled",
            source_root=source_root,
            runtime_root=runtime_root,
            working_directory=working_directory,
            projection_root=None,
            metadata_path=None,
            layout=None,
            invocation_style=None,
            probe_status="disabled_by_config",
            probe_details={},
        )

    if provider not in SUPPORTED_NATIVE_PROVIDERS:
        if mode == "require":
            raise ProviderNativeSkillError(
                f"Provider-native skills are not available for provider {provider!r}."
            )
        return ProviderNativeSkillProjection(
            provider=provider,
            mode=mode,
            status="fallback-only",
            source_root=source_root,
            runtime_root=runtime_root,
            working_directory=working_directory,
            projection_root=None,
            metadata_path=None,
            layout=None,
            invocation_style=None,
            probe_status="api_provider_fallback",
            probe_details={"reason": "API providers use FirmCLI load_skills fallback."},
        )

    manifests = load_provider_native_skill_manifests(
        source_root=source_root,
        provider=cast(ProviderNativeSkillProvider, provider),
    )
    if not manifests:
        if mode == "require":
            raise ProviderNativeSkillError(
                f"No active provider-native skill packages found for provider {provider!r} "
                f"under {source_root}."
            )
        return ProviderNativeSkillProjection(
            provider=provider,
            mode=mode,
            status="unavailable",
            source_root=source_root,
            runtime_root=runtime_root,
            working_directory=working_directory,
            projection_root=None,
            metadata_path=None,
            layout=None,
            invocation_style=None,
            probe_status="no_active_packages",
            probe_details={"source_root_exists": source_root.exists()},
        )

    layout_root = PROVIDER_LAYOUT_ROOTS[provider]
    projection_root = working_directory / layout_root
    projection_root.mkdir(parents=True, exist_ok=True)
    source_hashes: dict[str, str] = {}
    projected_hashes: dict[str, str] = {}
    for manifest in manifests:
        target_root = projection_root / manifest.skill_id
        _replace_projected_tree(manifest.root, target_root, manifest=manifest, provider=provider)
        source_hashes.update(_hash_tree(manifest.root, prefix=f"{manifest.skill_id}/source/"))
        projected_hashes.update(_hash_tree(target_root, prefix=f"{manifest.skill_id}/projected/"))

    metadata_path = runtime_root / "firmcli-native-skills.json"
    projection = ProviderNativeSkillProjection(
        provider=provider,
        mode=mode,
        status="available",
        source_root=source_root,
        runtime_root=runtime_root,
        working_directory=working_directory,
        projection_root=projection_root,
        metadata_path=metadata_path,
        layout=layout_root.as_posix(),
        invocation_style=PROVIDER_INVOCATION_STYLES[provider],
        probe_status="phase0_burner_skill_proven",
        probe_details=_phase0_probe_details(provider),
        manifests=manifests,
        source_hashes=source_hashes,
        projected_hashes=projected_hashes,
    )
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(
            {
                "generated_at_unix": time.time(),
                **projection.to_record(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return projection


def load_provider_native_skill_manifests(
    *,
    source_root: Path,
    provider: ProviderNativeSkillProvider,
) -> tuple[ProviderNativeSkillManifest, ...]:
    if not source_root.exists():
        return ()
    manifests_by_id: dict[str, ProviderNativeSkillManifest] = {}
    for variant in ("common", PROVIDER_VARIANT_DIRS[provider]):
        variant_root = source_root / variant
        if not variant_root.exists():
            continue
        for child in sorted(path for path in variant_root.iterdir() if path.is_dir()):
            manifest = load_provider_native_skill_manifest(child)
            if manifest.source_status == "disabled":
                continue
            if provider not in manifest.providers:
                continue
            manifests_by_id[manifest.skill_id] = manifest
    ordered = tuple(manifests_by_id[key] for key in sorted(manifests_by_id))
    return _resolve_dependency_order(ordered)


def load_provider_native_skill_manifest(root: Path) -> ProviderNativeSkillManifest:
    root = root.resolve()
    raw = _load_manifest_mapping(root)
    skill_id = _required_str(raw, "skill_id")
    if skill_id != root.name:
        raise ProviderNativeSkillError(
            f"Provider-native skill manifest id {skill_id!r} does not match folder {root.name!r}."
        )
    providers = _provider_tuple(raw.get("providers"))
    native_invocation = _native_invocation_map(raw.get("native_invocation"))
    manifest = ProviderNativeSkillManifest(
        skill_id=skill_id,
        title=_optional_str(raw, "title", skill_id),
        description=_optional_str(raw, "description", ""),
        providers=providers,
        native_invocation=native_invocation,
        fallback_skill_ids=_string_tuple(raw.get("fallback_skill_ids")),
        root=root,
        depends_on=_string_tuple(raw.get("depends_on")),
        context_files=_string_tuple(raw.get("context_files"), default=("SKILL.md",)),
        usable_paths=_string_tuple(raw.get("usable_paths")),
        requires_governed_actions=_string_tuple(raw.get("requires_governed_actions")),
        source_status=_optional_str(raw, "source_status", "active"),
    )
    _validate_manifest_paths(manifest)
    return manifest


def _load_manifest_mapping(root: Path) -> dict[object, object]:
    for name in MANIFEST_NAMES:
        path = root / name
        if path.is_file():
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ProviderNativeSkillError(f"Manifest must be a mapping: {path}")
            return raw
    raise ProviderNativeSkillError(f"Provider-native skill has no manifest: {root}")


def _validate_manifest_paths(manifest: ProviderNativeSkillManifest) -> None:
    for relative_path in (*manifest.context_files, *manifest.usable_paths):
        path = _safe_child_path(manifest.root, relative_path)
        if not path.exists():
            raise ProviderNativeSkillError(
                f"Provider-native skill path missing for {manifest.skill_id!r}: {relative_path}"
            )
    skill_md = _safe_child_path(manifest.root, "SKILL.md")
    if not skill_md.is_file():
        raise ProviderNativeSkillError(
            f"Provider-native skill {manifest.skill_id!r} must include SKILL.md."
        )


def _resolve_dependency_order(
    manifests: tuple[ProviderNativeSkillManifest, ...],
) -> tuple[ProviderNativeSkillManifest, ...]:
    by_id = {manifest.skill_id: manifest for manifest in manifests}
    ordered: list[ProviderNativeSkillManifest] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(skill_id: str) -> None:
        if skill_id in visited:
            return
        if skill_id in visiting:
            cycle = " -> ".join((*visiting, skill_id))
            raise ProviderNativeSkillError(f"Provider-native skill dependency cycle: {cycle}")
        manifest = by_id.get(skill_id)
        if manifest is None:
            raise ProviderNativeSkillError(
                f"Provider-native skill dependency {skill_id!r} is missing."
            )
        visiting.append(skill_id)
        for dependency in manifest.depends_on:
            visit(dependency)
        visiting.pop()
        visited.add(skill_id)
        ordered.append(manifest)

    for manifest in manifests:
        visit(manifest.skill_id)
    return tuple(ordered)


def _replace_projected_tree(
    source_root: Path,
    target_root: Path,
    *,
    manifest: ProviderNativeSkillManifest,
    provider: str,
) -> None:
    if target_root.exists():
        marker_path = target_root / PROJECTION_MARKER_NAME
        if not marker_path.is_file():
            raise ProviderNativeSkillError(
                "Refusing to overwrite existing provider-native skill directory without "
                f"FirmCLI projection marker: {target_root}"
            )
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)
    (target_root / PROJECTION_MARKER_NAME).write_text(
        json.dumps(
            {
                "generated_by": "FirmCLI provider-native skill projection",
                "provider": provider,
                "skill_id": manifest.skill_id,
                "source_root": str(source_root),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _hash_tree(root: Path, *, prefix: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        hashes[prefix + relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _phase0_probe_details(provider: str) -> dict[str, object]:
    if provider == "claude-cli":
        return {
            "source": "r12-provider-native-skill-bridge_probe_notes",
            "evidence": ".claude/skills works in claude --print --output-format json when Skill(skill-id) is allowed.",
            "requires_command_allowance": "Skill(skill-id)",
            "json_schema_mode": "unusable_in_probe_hung",
        }
    if provider == "codex-cli":
        return {
            "source": "r12-provider-native-skill-bridge_probe_notes",
            "evidence": ".codex/skills and .agents/skills worked in codex exec; .codex/skills is the selected runtime layout.",
        }
    return {}


def _safe_child_path(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ProviderNativeSkillError(
            f"Provider-native skill path escapes skill root: {relative_path}"
        )
    return candidate


def _required_str(raw: dict[object, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderNativeSkillError(f"Provider-native skill manifest missing {key!r}.")
    return value.strip()


def _optional_str(raw: dict[object, object], key: str, default: str) -> str:
    value = raw.get(key)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ProviderNativeSkillError(
            f"Provider-native skill manifest field {key!r} must be a string."
        )
    return value.strip()


def _string_tuple(value: object, *, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    if value is None:
        return default
    if not isinstance(value, list):
        raise ProviderNativeSkillError("Provider-native skill manifest list fields must be arrays.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ProviderNativeSkillError(
                "Provider-native skill manifest list items must be non-empty strings."
            )
        items.append(item.strip())
    return tuple(dict.fromkeys(items))


def _provider_tuple(value: object) -> tuple[ProviderNativeSkillProvider, ...]:
    raw_values = _string_tuple(value)
    if not raw_values:
        raise ProviderNativeSkillError(
            "Provider-native skill manifest providers must not be empty."
        )
    providers: list[ProviderNativeSkillProvider] = []
    for raw_provider in raw_values:
        if raw_provider not in SUPPORTED_NATIVE_PROVIDERS:
            raise ProviderNativeSkillError(
                f"Unsupported provider-native skill provider: {raw_provider!r}."
            )
        providers.append(cast(ProviderNativeSkillProvider, raw_provider))
    return tuple(providers)


def _native_invocation_map(value: object) -> dict[str, str]:
    if isinstance(value, str):
        return {"*": value.strip()}
    if not isinstance(value, dict):
        raise ProviderNativeSkillError(
            "Provider-native skill manifest native_invocation must be a string or mapping."
        )
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str) or not item.strip():
            raise ProviderNativeSkillError(
                "Provider-native skill manifest native_invocation entries must be non-empty strings."
            )
        result[key.strip()] = item.strip()
    return result


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
