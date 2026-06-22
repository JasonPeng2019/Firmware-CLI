<#
.SYNOPSIS
  Install the Firmware-CLI superpowers skills into a target .claude/skills directory
  so they are reusable beyond this repo (globally for you, or in another project).

.DESCRIPTION
  Idempotent and OS-appropriate. For each skill folder named in skills.manifest it
  creates an entry under the target directory. Default mode is 'link' (a Windows
  directory junction) so edits in this repo stay reflected everywhere; use -Mode copy
  for a detached, fully portable copy (e.g. for another machine or to vendor into a repo).

  Runs sync_references first so the installed skills carry their full reference text.

.PARAMETER Target
  Destination skills directory. Default: $HOME\.claude\skills (your personal global skills).
  Pass another project's <repo>\.claude\skills to install there.

.PARAMETER Mode
  'link'  (default) — directory junction back to this repo (auto-updating, not portable off this machine).
  'copy'           — independent copy (portable; re-run to update).

.PARAMETER Force
  Replace an existing entry of the same name at the target.

.EXAMPLE
  pwsh .claude/skills/install_skills.ps1
  pwsh .claude/skills/install_skills.ps1 -Target D:\work\other-repo\.claude\skills -Mode copy
#>
[CmdletBinding()]
param(
    [string]$Target = (Join-Path $HOME '.claude\skills'),
    [ValidateSet('link','copy')][string]$Mode = 'link',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$skillsDir = $PSScriptRoot

# 1. keep the reference text current before installing
& (Join-Path $skillsDir 'sync_references.ps1') | Out-Null

# 2. ensure target exists
if (-not (Test-Path $Target)) { New-Item -ItemType Directory -Path $Target -Force | Out-Null }

$manifest = Join-Path $skillsDir 'skills.manifest'
$installed = @()

foreach ($line in Get-Content $manifest) {
    $trimmed = $line.Trim()
    if ($trimmed -eq '' -or $trimmed.StartsWith('#')) { continue }
    $skill = ($trimmed -split '\s+', 2)[0]
    $srcSkill = Join-Path $skillsDir $skill
    if (-not (Test-Path $srcSkill)) { Write-Warning "skill folder missing, skipping: $skill"; continue }

    $dest = Join-Path $Target $skill
    if (Test-Path $dest) {
        if ($Force) { Remove-Item $dest -Recurse -Force }
        else { Write-Output "exists, skipping (use -Force to replace): $skill"; continue }
    }

    if ($Mode -eq 'link') {
        cmd /c mklink /J "$dest" "$srcSkill" | Out-Null
    } else {
        Copy-Item -Path $srcSkill -Destination $dest -Recurse -Force
    }
    $installed += $skill
}

Write-Output ""
Write-Output ("Installed " + $installed.Count + " skill(s) into $Target (mode=$Mode):")
$installed | ForEach-Object { Write-Output "  $_" }
Write-Output ""
Write-Output "Restart Claude Code (or /reload-skills) for the target to pick them up."
