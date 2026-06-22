<#
.SYNOPSIS
  Regenerate each superpowers skill's reference/ copy from the canonical playbook
  in ../../superpowers/. Source of truth stays superpowers/; the skill reference
  copies are generated artifacts so every skill is self-contained and portable
  without the playbooks ever drifting.

.DESCRIPTION
  Idempotent: safe to run repeatedly. Reads skills.manifest (skill-dir -> playbook),
  copies superpowers/<playbook> into <skill-dir>/reference/<playbook>, and reports
  any source playbook that is missing or any skill whose copy changed.

.EXAMPLE
  pwsh .claude/skills/sync_references.ps1
  pwsh .claude/skills/sync_references.ps1 -Check   # verify in sync, change nothing (CI use)
#>
[CmdletBinding()]
param(
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$skillsDir   = $PSScriptRoot
$repoRoot    = (Resolve-Path (Join-Path $skillsDir '..\..')).Path
$superpowers = Join-Path $repoRoot 'superpowers'
$manifest    = Join-Path $skillsDir 'skills.manifest'

if (-not (Test-Path $manifest)) { throw "manifest not found: $manifest" }

$drift = @()
$missing = @()

foreach ($line in Get-Content $manifest) {
    $trimmed = $line.Trim()
    if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
    $parts = $trimmed -split '\s+', 2
    if ($parts.Count -lt 2) { continue }
    $skill = $parts[0]
    $playbook = $parts[1].Trim()

    $src = Join-Path $superpowers $playbook
    if (-not (Test-Path $src)) { $missing += "$playbook (for $skill)"; continue }

    $refDir = Join-Path (Join-Path $skillsDir $skill) 'reference'
    $dst = Join-Path $refDir $playbook

    $srcHash = (Get-FileHash $src -Algorithm SHA256).Hash
    $dstHash = if (Test-Path $dst) { (Get-FileHash $dst -Algorithm SHA256).Hash } else { '' }

    if ($srcHash -ne $dstHash) {
        $drift += "$skill/reference/$playbook"
        if (-not $Check) {
            if (-not (Test-Path $refDir)) { New-Item -ItemType Directory -Path $refDir -Force | Out-Null }
            Copy-Item -Path $src -Destination $dst -Force
        }
    }
}

if ($missing.Count -gt 0) {
    Write-Warning ("Missing source playbooks:`n  " + ($missing -join "`n  "))
}

if ($Check) {
    if ($drift.Count -gt 0) {
        Write-Error ("Skill references are OUT OF SYNC (run without -Check to fix):`n  " + ($drift -join "`n  "))
        exit 1
    }
    Write-Output 'Skill references are in sync.'
} else {
    if ($drift.Count -gt 0) {
        Write-Output ("Synced " + $drift.Count + " reference file(s):`n  " + ($drift -join "`n  "))
    } else {
        Write-Output 'Already in sync; nothing to do.'
    }
}
if ($missing.Count -gt 0) { exit 2 }
