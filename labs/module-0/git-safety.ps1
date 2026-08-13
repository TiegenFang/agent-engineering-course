<#!
.SYNOPSIS
  Produce a privacy-safe Git safety lab fixture for module 0.

.DESCRIPTION
  The script only observes an explicitly selected local repository.  It does
  not create commits, switch branches, delete files, contact a remote, or
  print Git output.  Use it after the learner has completed the commands in
  the lesson inside a disposable practice repository.  The checks confirm the
  command seam and the final recovery/ignore state; the learner still records
  why each command was safe before asking a human to commit.

  The default repository is the current directory, so the lesson always asks
  learners to pass -RepoPath explicitly.  -OutputPath is optional and uses an
  atomic replacement so a repair-and-rerun loop can be repeated safely.
#>
[CmdletBinding()]
param(
  [string]$RepoPath = ".",
  [string]$SecretPath = "secrets/local.env",
  [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-GitReadOnly {
  param(
    [Parameter(Mandatory)] [string[]]$Arguments
  )

  try {
    $raw = (& git @Arguments 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
    return [pscustomobject]@{
      ExitCode = $exitCode
      Output = $raw
    }
  }
  catch {
    return [pscustomobject]@{
      ExitCode = 127
      Output = ""
    }
  }
}

function Test-GitCommandSucceeded {
  param([Parameter(Mandatory)] [pscustomobject]$Result)

  return $Result.ExitCode -eq 0
}

function Test-GitDiffCommandRan {
  param([Parameter(Mandatory)] [pscustomobject]$Result)

  # git diff --quiet uses exit code 1 to mean "there are differences".
  return $Result.ExitCode -in @(0, 1)
}

function New-Check {
  param(
    [Parameter(Mandatory)] [string]$Id,
    [Parameter(Mandatory)] [bool]$Passed
  )

  return [ordered]@{
    id = $Id
    result = if ($Passed) { "passed" } else { "failed" }
  }
}

function Write-AnonymousFixture {
  param(
    [Parameter(Mandatory)] [string]$Encoded,
    [Parameter(Mandatory)] [string]$TargetPath
  )

  try {
    $target = [System.IO.Path]::GetFullPath($TargetPath)
    $parent = [System.IO.Path]::GetDirectoryName($target)
    if ([string]::IsNullOrWhiteSpace($parent) -or
      -not (Test-Path -LiteralPath $parent -PathType Container)) {
      throw "Output directory does not exist."
    }

    $temporaryTarget = Join-Path $parent ("." + [System.IO.Path]::GetRandomFileName())
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    try {
      [System.IO.File]::WriteAllText($temporaryTarget, $Encoded, $utf8)
      [System.IO.File]::Move($temporaryTarget, $target, $true)
    }
    finally {
      if ([System.IO.File]::Exists($temporaryTarget)) {
        [System.IO.File]::Delete($temporaryTarget)
      }
    }
  }
  catch {
    throw "Could not write the Git safety fixture."
  }
}

$checks = [System.Collections.Generic.List[object]]::new()
$repo = $null
$repoReady = $false
try {
  $repo = [System.IO.Path]::GetFullPath($RepoPath)
  $repoReady = Test-Path -LiteralPath $repo -PathType Container
}
catch {
  $repoReady = $false
}

$status = $null
$hasHead = $null
$branch = $null
$history = $null
$ignore = $null
$trackedSecret = $null
$diff = $null
$stagedDiff = $null
$trackedFiles = $null

if ($repoReady) {
  $gitPrefix = @("-C", $repo)
  $inside = Invoke-GitReadOnly -Arguments ($gitPrefix + @("rev-parse", "--is-inside-work-tree"))
  $status = Invoke-GitReadOnly -Arguments ($gitPrefix + @("status", "--short", "--branch"))
  $hasHead = Invoke-GitReadOnly -Arguments ($gitPrefix + @("rev-parse", "--verify", "HEAD"))
  $branch = Invoke-GitReadOnly -Arguments ($gitPrefix + @("branch", "--show-current"))
  $history = Invoke-GitReadOnly -Arguments ($gitPrefix + @("log", "-1", "--format=%h"))
  $diff = Invoke-GitReadOnly -Arguments ($gitPrefix + @("diff", "--quiet"))
  $stagedDiff = Invoke-GitReadOnly -Arguments ($gitPrefix + @("diff", "--cached", "--quiet"))
  $trackedFiles = Invoke-GitReadOnly -Arguments ($gitPrefix + @("ls-files"))
  $ignore = Invoke-GitReadOnly -Arguments ($gitPrefix + @("check-ignore", "--quiet", "--", $SecretPath))
  $trackedSecret = Invoke-GitReadOnly -Arguments (
    $gitPrefix + @("ls-files", "--error-unmatch", "--", $SecretPath)
  )
}
else {
  $inside = [pscustomobject]@{ ExitCode = 1; Output = "" }
}

if ($null -eq $status) { $status = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $hasHead) { $hasHead = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $branch) { $branch = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $history) { $history = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $ignore) { $ignore = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $trackedSecret) { $trackedSecret = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $diff) { $diff = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $stagedDiff) { $stagedDiff = [pscustomobject]@{ ExitCode = 1; Output = "" } }
if ($null -eq $trackedFiles) { $trackedFiles = [pscustomobject]@{ ExitCode = 1; Output = "" } }

$statusLines = @()
if ($null -ne $status) {
  $statusLines = @(
    ([string]$status.Output -split "`r?`n") |
      Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and $_ -notlike "##*" }
  )
}

$checks.Add((New-Check -Id "status-baseline" -Passed (
  (Test-GitCommandSucceeded -Result $inside) -and
  (Test-GitCommandSucceeded -Result $status)
)))
$checks.Add((New-Check -Id "diff-reviewed" -Passed (
  (Test-GitDiffCommandRan -Result $diff) -and
  (Test-GitDiffCommandRan -Result $stagedDiff)
)))
$checks.Add((New-Check -Id "selective-stage" -Passed (
  (Test-GitCommandSucceeded -Result $hasHead) -and
  (Test-GitCommandSucceeded -Result $trackedFiles) -and
  -not [string]::IsNullOrWhiteSpace([string]$trackedFiles.Output)
)))
$checks.Add((New-Check -Id "intentional-commit" -Passed (
  (Test-GitCommandSucceeded -Result $hasHead) -and
  -not [string]::IsNullOrWhiteSpace([string]$hasHead.Output)
)))
$checks.Add((New-Check -Id "branch-inspected" -Passed (
  (Test-GitCommandSucceeded -Result $branch) -and
  -not [string]::IsNullOrWhiteSpace([string]$branch.Output)
)))
$checks.Add((New-Check -Id "history-inspected" -Passed (
  (Test-GitCommandSucceeded -Result $history) -and
  -not [string]::IsNullOrWhiteSpace([string]$history.Output)
)))
$checks.Add((New-Check -Id "secret-ignored" -Passed (
  (Test-GitCommandSucceeded -Result $ignore) -and
  $trackedSecret.ExitCode -ne 0
)))
$checks.Add((New-Check -Id "recovery-complete" -Passed (
  (Test-GitCommandSucceeded -Result $hasHead) -and
  (Test-GitCommandSucceeded -Result $status) -and
  $statusLines.Count -eq 0
)))

$platform = if ($IsWindows) {
  "windows"
}
elseif ($IsMacOS) {
  "macos"
}
elseif ($IsLinux) {
  "linux"
}
else {
  "unknown"
}

$diagnostic = [ordered]@{
  lesson_id = "t06-git-safety"
  platform = $platform
  shell = "powershell"
  checks = @($checks)
}
$encoded = $diagnostic | ConvertTo-Json -Depth 4

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $encoded
  exit 0
}

try {
  Write-AnonymousFixture -Encoded $encoded -TargetPath $OutputPath
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
