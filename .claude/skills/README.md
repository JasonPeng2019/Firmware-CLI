# Superpowers Skills

This folder turns the Firmware-CLI **superpowers playbooks** (`../../superpowers/*.md`) into
Claude Code **Agent Skills** — folder-per-skill `SKILL.md` files that Claude *auto-loads by description*
when a task matches, instead of relying on an agent to remember to read the playbook.

## Skills vs. the slash commands

- **`.claude/commands/*.md`** — slash **commands** (`/specs`, `/build`, `/review`, …): *you* invoke them
  by typing the slash. (See `superpowers-spec-loop`.)
- **`.claude/skills/<name>/SKILL.md`** — **skills**: the *model* invokes them automatically when your
  request matches the skill's `description:`. This is how "read the relevant playbook based on what your
  task touches" gets enforced by the harness rather than by memory.

## Layout

```
.claude/skills/
├── skills.manifest              # data: skill-dir -> source playbook
├── README.md                    # this file
├── sync_references.{ps1,sh}     # regenerate each skill's reference/ from ../../superpowers/
├── install_skills.{ps1,sh}      # install skills to ~/.claude/skills or another project
└── superpowers-<name>/
    ├── SKILL.md                 # concise, auto-triggered rule (hand-authored)
    └── reference/<playbook>.md  # full playbook text (GENERATED — do not hand-edit)
```

## Source of truth & no drift

The **canonical playbooks stay in `../../superpowers/`** — that is the one editing home (doc-sync rule:
one fact, one home). Each skill's `reference/<playbook>.md` is a **generated copy**, produced by
`sync_references`. Edit a playbook in `superpowers/`, then run the sync; never hand-edit a `reference/`
file. `SKILL.md` itself is the hand-authored concise/trigger layer and points to its reference for the
full text.

## Workflows

Regenerate references after editing any playbook (idempotent):

```powershell
pwsh .claude/skills/sync_references.ps1            # Windows
```
```bash
./.claude/skills/sync_references.sh                # macOS / Git Bash
```

Verify in sync without changing anything (good for CI / pre-commit):

```bash
./.claude/skills/sync_references.sh --check
```

Install the skills for reuse beyond this repo:

```powershell
# personal/global — auto-updating junctions back to this repo:
pwsh .claude/skills/install_skills.ps1
# into another project, as a detached portable copy:
pwsh .claude/skills/install_skills.ps1 -Target D:\work\other-repo\.claude\skills -Mode copy
```
```bash
./.claude/skills/install_skills.sh                                   # link into ~/.claude/skills
./.claude/skills/install_skills.sh --target /path/repo/.claude/skills --mode copy
```

`link` mode (default) creates a junction/symlink so repo edits stay reflected everywhere on this machine;
`copy` mode makes an independent, portable copy for another machine or to vendor into a repo. Both are
idempotent (re-run safely; `--force` / `-Force` replaces an existing entry).

After installing, restart Claude Code or run `/reload-skills` so the target picks them up.

## Adding a new skill

1. Write the playbook in `../../superpowers/<your_playbook>.md` (the source of truth).
2. Create `superpowers-<name>/SKILL.md` here (frontmatter `name` + a sharp `description:` trigger; a
   concise body ending with `Full playbook: reference/<your_playbook>.md`).
3. Add a row to `skills.manifest`: `superpowers-<name>   <your_playbook>.md`.
4. Run `sync_references` to populate `reference/`.

## These skills are tuned to this project

The rules reference this repo's build plan, board layout, MCP server, and `uv` command surface. They are
portable to install anywhere, but their *content* assumes the Firmware-CLI project; adapt the references
if you reuse them elsewhere.
