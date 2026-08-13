<#!
.SYNOPSIS
  Produce a privacy-safe environment diagnostic fixture for module 0.

.DESCRIPTION
  The script checks only command visibility, version execution, and manually
  confirmed account/editor readiness.  It never prints command paths, reads
  source files, calls the network, or inspects identity-bearing variables.
  The resulting JSON is an input fixture for the existing course_check
  evidence command; course_check emits the browser-facing anonymous contract.
#>
[CmdletBinding()]
param(
  [switch]$EditorReady,
  [switch]$GitHubReady,
  [ValidateSet("none", "codex", "claude", "both")]
  [string]$CodingAgent = "none",
  # Raising this value is a deterministic, read-only fault-injection path.
  [ValidateRange(3, 99)]
  [int]$MinimumPythonMajor = 3,
  [string]$OutputPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-Check {
  param(
    [Parameter(Mandatory)] [string]$Id,
    [Parameter(Mandatory)] [bool]$Passed
  )

  [ordered]@{
    id = $Id
    result = if ($Passed) { "passed" } else { "failed" }
  }
}

function Test-CommandVisible {
  param([Parameter(Mandatory)] [string]$Name)

  $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
  if ($null -eq $command) {
    return $false
  }
  return $command.CommandType -in @("Application", "ExternalScript")
}

function Get-VersionState {
  param(
    [Parameter(Mandatory)] [string]$Name,
    [Parameter(Mandatory)] [int]$MinimumMajor,
    [int]$MinimumMinor = 0
  )

  $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
  if ($null -eq $command -or $command.CommandType -notin @("Application", "ExternalScript")) {
    return [ordered]@{ available = $false; meets = $false }
  }

  try {
    $versionArguments = @("--version")
    $rawVersion = (& $command.Source @versionArguments 2>&1 | Out-String).Trim()
    $exitCode = $LASTEXITCODE
  }
  catch {
    return [ordered]@{ available = $true; meets = $false }
  }

  if ($exitCode -ne 0) {
    return [ordered]@{ available = $true; meets = $false }
  }

  $match = [regex]::Match($rawVersion, "(?<!\d)(\d+)\.(\d+)(?:\.(\d+))?")
  if (-not $match.Success) {
    return [ordered]@{ available = $true; meets = $false }
  }

  $major = [int]$match.Groups[1].Value
  $minor = [int]$match.Groups[2].Value
  $meets = ($major -gt $MinimumMajor) -or (
    $major -eq $MinimumMajor -and $minor -ge $MinimumMinor
  )
  return [ordered]@{ available = $true; meets = $meets }
}

$checks = [System.Collections.Generic.List[object]]::new()
$powerShellVersion = $PSVersionTable.PSVersion
$checks.Add((New-Check -Id "powershell-7" -Passed ($powerShellVersion.Major -ge 7)))

$editorVisible = @("code", "code-insiders", "notepad++") |
  Where-Object { Test-CommandVisible -Name $_ } |
  Select-Object -First 1
$checks.Add((New-Check -Id "editor-command" -Passed ($EditorReady -or $null -ne $editorVisible)))

$pythonState = Get-VersionState -Name "python" -MinimumMajor $MinimumPythonMajor -MinimumMinor 11
$checks.Add((New-Check -Id "python-on-path" -Passed $pythonState.available))
$checks.Add((New-Check -Id "python-version" -Passed $pythonState.meets))

$gitState = Get-VersionState -Name "git" -MinimumMajor 2
$checks.Add((New-Check -Id "git-on-path" -Passed $gitState.available))
$checks.Add((New-Check -Id "git-version" -Passed $gitState.meets))

$checks.Add((New-Check -Id "github-account" -Passed $GitHubReady))
$checks.Add((New-Check -Id "coding-agent-account" -Passed ($CodingAgent -ne "none")))

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
  lesson_id = "t05-environment"
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
  $target = [System.IO.Path]::GetFullPath($OutputPath)
  if ([System.IO.File]::Exists($target)) {
    throw "Output file already exists; choose another name."
  }
  $parent = [System.IO.Path]::GetDirectoryName($target)
  if ([string]::IsNullOrWhiteSpace($parent) -or -not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw "Output directory does not exist."
  }
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($target, $encoded, $utf8)
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
