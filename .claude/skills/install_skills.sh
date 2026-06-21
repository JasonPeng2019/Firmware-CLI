#!/usr/bin/env bash
# Install the Firmware-CLI superpowers skills into a target .claude/skills directory
# so they are reusable beyond this repo (globally for you, or in another project).
#
# Idempotent and OS-appropriate. For each skill folder named in skills.manifest it
# creates an entry under the target directory. Default mode is 'link' (a symlink) so
# edits in this repo stay reflected everywhere; use --mode copy for a detached,
# fully portable copy. Runs sync_references first so installed skills carry full text.
#
# Usage:
#   ./.claude/skills/install_skills.sh                         # link into ~/.claude/skills
#   ./.claude/skills/install_skills.sh --mode copy             # independent copy
#   ./.claude/skills/install_skills.sh --target /path/.claude/skills --force
set -euo pipefail

TARGET="$HOME/.claude/skills"
MODE="link"
FORCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="$2"; shift 2;;
    --mode)   MODE="$2";   shift 2;;
    --force)  FORCE=1;     shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

skills_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
manifest="$skills_dir/skills.manifest"

# 1. keep reference text current before installing
"$skills_dir/sync_references.sh" >/dev/null

# 2. ensure target exists
mkdir -p "$TARGET"

installed=0
while read -r skill _rest; do
  case "$skill" in ''|\#*) continue;; esac
  src_skill="$skills_dir/$skill"
  [ -d "$src_skill" ] || { echo "WARN: skill folder missing, skipping: $skill" >&2; continue; }

  dest="$TARGET/$skill"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$FORCE" -eq 1 ]; then rm -rf "$dest";
    else echo "exists, skipping (use --force to replace): $skill"; continue; fi
  fi

  if [ "$MODE" = "link" ]; then ln -s "$src_skill" "$dest";
  else cp -R "$src_skill" "$dest"; fi
  echo "  $skill"
  installed=$((installed + 1))
done < "$manifest"

echo ""
echo "Installed $installed skill(s) into $TARGET (mode=$MODE)."
echo "Restart Claude Code (or /reload-skills) for the target to pick them up."
