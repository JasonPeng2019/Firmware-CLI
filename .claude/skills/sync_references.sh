#!/usr/bin/env bash
# Regenerate each superpowers skill's reference/ copy from the canonical playbook
# in ../../superpowers/. Source of truth stays superpowers/; the skill reference
# copies are generated artifacts so every skill is self-contained and portable
# without the playbooks ever drifting.
#
# Idempotent: safe to run repeatedly. Reads skills.manifest (skill-dir -> playbook).
#
# Usage:
#   ./.claude/skills/sync_references.sh           # sync (copy changed references)
#   ./.claude/skills/sync_references.sh --check    # verify in sync, change nothing (CI use)
set -euo pipefail

CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

skills_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$skills_dir/../.." && pwd)"
superpowers="$repo_root/superpowers"
manifest="$skills_dir/skills.manifest"

[ -f "$manifest" ] || { echo "manifest not found: $manifest" >&2; exit 1; }

hash_of() { # portable sha256 (Linux: sha256sum, macOS: shasum -a 256)
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}';
  else shasum -a 256 "$1" | awk '{print $1}'; fi
}

drift=0
missing=0

while read -r skill playbook _rest; do
  case "$skill" in ''|\#*) continue;; esac
  [ -n "${playbook:-}" ] || continue

  src="$superpowers/$playbook"
  if [ ! -f "$src" ]; then
    echo "WARN: missing source playbook: $playbook (for $skill)" >&2
    missing=1
    continue
  fi

  ref_dir="$skills_dir/$skill/reference"
  dst="$ref_dir/$playbook"

  src_hash="$(hash_of "$src")"
  dst_hash=""
  [ -f "$dst" ] && dst_hash="$(hash_of "$dst")"

  if [ "$src_hash" != "$dst_hash" ]; then
    drift=$((drift + 1))
    echo "  $skill/reference/$playbook"
    if [ "$CHECK" -eq 0 ]; then
      mkdir -p "$ref_dir"
      cp -f "$src" "$dst"
    fi
  fi
done < "$manifest"

if [ "$CHECK" -eq 1 ]; then
  if [ "$drift" -gt 0 ]; then
    echo "Skill references are OUT OF SYNC (run without --check to fix)." >&2
    exit 1
  fi
  echo "Skill references are in sync."
else
  if [ "$drift" -gt 0 ]; then echo "Synced $drift reference file(s)."; else echo "Already in sync; nothing to do."; fi
fi
[ "$missing" -eq 1 ] && exit 2 || true
