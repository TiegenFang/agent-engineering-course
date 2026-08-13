<#!
.SYNOPSIS
  Create a disposable, local Git repository for the Codex telemetry task.

.DESCRIPTION
  Copies the checked-in synthetic starter into a new directory and records a
  local baseline commit.  The target must be explicit and empty.  No network,
  remote, credential, or course-repository operation is performed.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$WorkspacePath,
  [Parameter(Mandatory)]
  [switch]$ConfirmTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Native {
  param(
    [Parameter(Mandatory)] [string]$File,
    [Parameter(Mandatory)] [string[]]$Arguments
  )

  try {
    $output = (& $File @Arguments 2>&1 | Out-String).TrimEnd()
    $exitCode = $LASTEXITCODE
  }
  catch {
    throw "Unable to run ${File}: $($_.Exception.Message)"
  }
  if ($exitCode -ne 0) {
    throw "$File failed with exit code $exitCode."
  }
  return $output
}

if (-not $ConfirmTarget) {
  throw "Pass -ConfirmTarget after choosing a disposable practice directory."
}

try {
  $target = [System.IO.Path]::GetFullPath($WorkspacePath)
}
catch {
  throw "WorkspacePath is not a valid path."
}

$root = [System.IO.Path]::GetPathRoot($target)
if ([string]::Equals($root, $target, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "WorkspacePath must not be a drive root."
}
$parent = [System.IO.Path]::GetDirectoryName($target)
if ([string]::IsNullOrWhiteSpace($parent) -or -not (Test-Path -LiteralPath $parent -PathType Container)) {
  throw "WorkspacePath parent must already exist."
}
if (Test-Path -LiteralPath $target) {
  $existing = @(Get-ChildItem -LiteralPath $target -Force)
  if ($existing.Count -ne 0) {
    throw "WorkspacePath must be new or empty; no files were removed."
  }
}
else {
  New-Item -ItemType Directory -Path $target | Out-Null
}

$starter = Join-Path $PSScriptRoot "starter"
if (-not (Test-Path -LiteralPath $starter -PathType Container)) {
  throw "Starter directory is missing."
}
foreach ($item in @(Get-ChildItem -LiteralPath $starter -Force)) {
  Copy-Item -LiteralPath $item.FullName -Destination $target -Recurse -Force
}

$artifactStages = Join-Path $target "artifacts\codex-task-stages"
New-Item -ItemType Directory -Path $artifactStages -Force | Out-Null

$gitPrefix = @("-C", $target)
Invoke-Native -File "git" -Arguments ($gitPrefix + @("init", "--initial-branch=main")) | Out-Null
Invoke-Native -File "git" -Arguments ($gitPrefix + @("config", "user.name", "Course Learner")) | Out-Null
Invoke-Native -File "git" -Arguments ($gitPrefix + @("config", "user.email", "learner@example.invalid")) | Out-Null
Invoke-Native -File "git" -Arguments ($gitPrefix + @("add", ".")) | Out-Null
Invoke-Native -File "git" -Arguments ($gitPrefix + @("commit", "-m", "chore: create telemetry task baseline")) | Out-Null

[ordered]@{
  lesson_id = "t04-codex-repository-task"
  task_id = "telemetry-report-v1"
  baseline = "recorded"
  network = "not-used"
  target = "disposable-local-repository"
} | ConvertTo-Json -Compress
