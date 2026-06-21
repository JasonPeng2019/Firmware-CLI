"""Safe local workspace editing/build support for the turnkey brain."""

from __future__ import annotations

import difflib
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pyocd_debug_mcp.services.session_runtime import RUNS_ROOT

SNAPSHOT_ROOT = RUNS_ROOT / "_r12_snapshots"  # PROJECT-DEFINED (turnkey scratch area)


class WorkspaceError(RuntimeError):
    """Raised when the turnkey brain hits a workspace constraint or build error."""


@dataclass(frozen=True)
class BuildResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class WorkspaceSession:
    root: Path
    snapshot_root: Path
    allowed_edit_roots: tuple[str, ...]
    build_command: str | None
    code_edits_allowed: bool

    def read_file(self, relative_path: str) -> str:
        path = self._resolve_existing_file(relative_path)
        return path.read_text(encoding="utf-8")

    def replace_file(self, relative_path: str, content: str) -> Path:
        if not self.code_edits_allowed:
            raise WorkspaceError("Code edits are not allowed for this turnkey run.")
        path = self._resolve_editable_file(relative_path)
        path.write_text(content, encoding="utf-8")
        return path

    def run_build(self, command: str | None = None) -> BuildResult:
        build_command = (command or self.build_command or "").strip()
        if not build_command:
            raise WorkspaceError("No build command is available for this workspace.")
        try:
            result = subprocess.run(
                ["bash", "-lc", build_command],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise WorkspaceError("`bash` was not found while running the build command.") from exc
        return BuildResult(
            command=build_command,
            exit_code=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    def changed_files(self) -> tuple[str, ...]:
        before = self._relative_files(self.snapshot_root)
        after = self._relative_files(self.root)
        changed = sorted(
            path
            for path in set(before) | set(after)
            if before.get(path) != after.get(path)
        )
        return tuple(changed)

    def write_diff(self, output_path: Path) -> None:
        before = self._relative_files(self.snapshot_root)
        after = self._relative_files(self.root)
        chunks: list[str] = []
        for relative in sorted(set(before) | set(after)):
            before_bytes = before.get(relative)
            after_bytes = after.get(relative)
            if before_bytes == after_bytes:
                continue

            before_lines, before_binary = _decode_diff_text(before_bytes or b"")
            after_lines, after_binary = _decode_diff_text(after_bytes or b"")
            if before_binary or after_binary:
                chunks.append(f"Binary files a/{relative} and b/{relative} differ\n")
                continue

            diff_lines = difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
                lineterm="",
            )
            rendered = "\n".join(diff_lines)
            if rendered:
                chunks.append(rendered + "\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("".join(chunks), encoding="utf-8")

    def _resolve_existing_file(self, relative_path: str) -> Path:
        path = self._resolve_relative_path(relative_path)
        if not path.exists() or not path.is_file():
            raise WorkspaceError(f"Workspace file does not exist: {relative_path}")
        return path

    def _resolve_editable_file(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/").strip()
        if not normalized:
            raise WorkspaceError("Workspace edit path cannot be empty.")
        if self.allowed_edit_roots and not any(
            normalized == root or normalized.startswith(f"{root}/")
            for root in self.allowed_edit_roots
        ):
            allowed = ", ".join(self.allowed_edit_roots)
            raise WorkspaceError(
                f"Workspace edit path '{relative_path}' is outside the allowed edit roots: {allowed}"
            )
        return self._resolve_relative_path(normalized)

    def _resolve_relative_path(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(
                f"Workspace path '{relative_path}' escapes the workspace root."
            ) from exc
        return candidate

    def _relative_files(self, root: Path) -> dict[str, bytes]:
        output: dict[str, bytes] = {}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if "build" in relative.parts:
                continue
            if relative.name.startswith(".r12_"):
                continue
            output[str(relative).replace("\\", "/")] = path.read_bytes()
        return output


def _decode_diff_text(data: bytes) -> tuple[list[str], bool]:
    try:
        return data.decode("utf-8").splitlines(keepends=True), False
    except UnicodeDecodeError:
        return [], True


def prepare_workspace_session(
    *,
    workspace_root: Path,
    allowed_edit_roots: tuple[str, ...],
    build_command: str | None,
    code_edits_allowed: bool,
    label: str,
    copy_workspace: bool = False,
) -> WorkspaceSession:
    root = workspace_root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise WorkspaceError(f"Workspace root does not exist: {root}")
    if copy_workspace:
        copied_root = SNAPSHOT_ROOT / f"{label}-{secrets.token_hex(4)}" / "workspace"
        copied_root.parent.mkdir(parents=True, exist_ok=True)
        _copy_tree(root, copied_root)
        snapshot_root = copied_root.parent / "snapshot"
        _copy_tree(copied_root, snapshot_root)
        root = copied_root
    else:
        snapshot_root = SNAPSHOT_ROOT / f"{label}-{secrets.token_hex(4)}"
        snapshot_root.parent.mkdir(parents=True, exist_ok=True)
        _copy_tree(root, snapshot_root)
    return WorkspaceSession(
        root=root,
        snapshot_root=snapshot_root,
        allowed_edit_roots=allowed_edit_roots,
        build_command=build_command,
        code_edits_allowed=code_edits_allowed,
    )


def _copy_tree(source: Path, dest: Path) -> None:
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = dest / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
