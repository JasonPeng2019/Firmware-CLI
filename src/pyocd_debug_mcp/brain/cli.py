"""CLI frontage for the turnkey brain."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from pyocd_debug_mcp.brain.mcp_client import ServerCommand
from pyocd_debug_mcp.brain.runner import TurnkeyRunError, TurnkeyRunner
from pyocd_debug_mcp.brain.skills import DEFAULT_SKILLS_ROOT, SkillConfigError, load_skill_specs
from pyocd_debug_mcp.brain.models import TurnkeyRunRequest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Turnkey brain CLI for deterministic board health/repair workflows."
    )
    parser.add_argument(
        "--skills-root",
        default=str(DEFAULT_SKILLS_ROOT),
        help="Override the tracked turnkey skills directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-skills", help="List tracked turnkey skills.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the skills as JSON.",
    )

    run_parser = subparsers.add_parser("run", help="Run one turnkey skill on a board.")
    run_parser.add_argument("--board-id", required=True, help="Tracked board id to use.")
    run_parser.add_argument("--skill-id", required=True, help="Turnkey skill id to execute.")
    run_parser.add_argument("--case-id", help="Optional tracked benchmark case id for the run record.")
    run_parser.add_argument(
        "--workspace-root",
        help="Optional workspace root for repair-oriented skills.",
    )
    run_parser.add_argument(
        "--flash-artifact",
        help="Optional explicit flash artifact path. Relative paths resolve from --workspace-root when set.",
    )
    run_parser.add_argument(
        "--symbol-artifact",
        help="Optional explicit ELF/symbol artifact path. Relative paths resolve from --workspace-root when set.",
    )
    run_parser.add_argument(
        "--expected-uart-substring",
        help="Override the expected UART substring for this run.",
    )
    run_parser.add_argument(
        "--stage1-symbol-name",
        default="stage1_known_value",
        help="Override the Stage 1 symbol name used by turnkey checks.",
    )
    run_parser.add_argument(
        "--stage1-symbol-value-u32",
        default="0x1234ABCD",
        help="Override the expected Stage 1 symbol value.",
    )
    run_parser.add_argument(
        "--build-command",
        help="Optional local rebuild command for repair-oriented skills.",
    )
    run_parser.add_argument(
        "--initial-post-flash-state",
        choices=("running", "halted"),
        default="running",
        help="State the target should be left in after the initial flash.",
    )
    run_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the structured run summary as JSON.",
    )
    run_parser.add_argument(
        "--server-command",
        help="Override the server executable used for the child stdio MCP server.",
    )
    run_parser.add_argument(
        "--server-arg",
        action="append",
        default=[],
        help="Append one argument to the overridden server command.",
    )
    return parser


def _list_skills(skills_root: Path, *, as_json: bool) -> int:
    skills = load_skill_specs(skills_root)
    if as_json:
        payload = [
            {
                "skill_id": skill.skill_id,
                "title": skill.title,
                "supported_kinds": list(skill.supported_kinds),
                "workflow_kind": skill.workflow_kind,
                "requires_workspace": skill.requires_workspace,
                "source_path": str(skill.source_path),
            }
            for skill in skills
        ]
        print(json.dumps(payload, indent=2))
        return 0

    for skill in skills:
        supported = ", ".join(skill.supported_kinds)
        print(
            f"{skill.skill_id}: {skill.title} [{supported}] "
            f"workflow={skill.workflow_kind}"
        )
    return 0


def _server_command_from_args(args) -> ServerCommand | None:  # type: ignore[no-untyped-def]
    command = getattr(args, "server_command", None)
    if not command:
        return None
    return ServerCommand(command=command, args=tuple(args.server_arg or ()))


async def _run_command(args) -> int:  # type: ignore[no-untyped-def]
    skills_root = Path(args.skills_root).expanduser().resolve()
    runner = TurnkeyRunner(skills_root=skills_root)
    request = TurnkeyRunRequest(
        board_id=args.board_id,
        skill_id=args.skill_id,
        case_id=args.case_id,
        workspace_root=args.workspace_root,
        flash_artifact=args.flash_artifact,
        symbol_artifact=args.symbol_artifact,
        expected_uart_substring=args.expected_uart_substring,
        stage1_symbol_name=args.stage1_symbol_name,
        stage1_symbol_value_u32=args.stage1_symbol_value_u32,
        build_command=args.build_command,
        initial_post_flash_state=args.initial_post_flash_state,
    )
    result = await runner.run(request, server_command=_server_command_from_args(args))
    if getattr(args, "json", False):
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(
            f"{result.final_status}: board={result.board_id} skill={result.skill_id} "
            f"session_id={result.session_id or '(none)'} result={result.result_path}"
        )
    return 0 if result.final_status in {"success", "healthy_confirmed", "diagnosed_only", "fixed"} else 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    skills_root = Path(args.skills_root).expanduser().resolve()

    try:
        if args.command == "list-skills":
            return _list_skills(skills_root, as_json=bool(args.json))
        if args.command == "run":
            return asyncio.run(_run_command(args))
    except (SkillConfigError, TurnkeyRunError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
