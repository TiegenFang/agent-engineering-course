<#!
.SYNOPSIS
  Record privacy-safe, stage-by-stage evidence for the module 0 Git lab.

.DESCRIPTION
  This script is read-only with respect to the selected repository.  It does
  not create commits, switch branches, delete files, contact a remote, or
  modify repository files.  The learner calls it at fixed checkpoints while
  working in a disposable practice repository.  Each checkpoint observes a
  required state transition and writes one new status-only stage record into a
  pre-created artifacts/git-safety-stages directory.  The final checkpoint
  assembles the ordered trace and derives the eight public checks.

  The script requires an explicit -ReadOnlyConfirmed switch and an explicit
  repository path.  Output files must be new .json files directly below an
  artifacts directory; replacing an existing file requires -AllowOverwrite.
  Stage records are also new by default.  These restrictions keep a copied
  command from silently operating on a course, research, or enterprise
  repository and make the recovery loop repeatable only by explicit choice.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$RepoPath,
  [Parameter(Mandatory)]
  [ValidateSet(
    "baseline",
    "branch-history",
    "change-created",
    "selective-stage",
    "first-commit-decision",
    "first-commit-recorded",
    "secret-before",
    "secret-ignored",
    "secret-commit-decision",
    "secret-commit-recorded",
    "recovery-before",
    "recovery-recorded",
    "final"
  )]
  [string]$Stage,
  [Parameter(Mandatory)]
  [string]$EvidenceDirectory,
  [string]$OutputPath,
  [string]$SecretPath = "secrets/local.env",
  [string]$TrackedExercisePath = "README.md",
  [string]$UntrackedExercisePath = "notes.md",
  [switch]$HumanApproved,
  [Parameter(Mandatory)]
  [switch]$ReadOnlyConfirmed,
  [switch]$AllowOverwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stageOrder = @(
  "baseline",
  "branch-history",
  "change-created",
  "selective-stage",
  "first-commit-decision",
  "first-commit-recorded",
  "secret-before",
  "secret-ignored",
  "secret-commit-decision",
  "secret-commit-recorded",
  "recovery-before",
  "recovery-recorded",
  "final"
)

function Assert-RelativePath {
  param(
    [Parameter(Mandatory)] [string]$Value,
    [Parameter(Mandatory)] [string]$Label
  )

  if ([string]::IsNullOrWhiteSpace($Value) -or [System.IO.Path]::IsPathRooted($Value)) {
    throw "$Label must be a non-empty relative path."
  }
  $parts = $Value.Replace("/", "\").Split([char]"\")
  if ($parts -contains ".." -or $parts -contains "") {
    throw "$Label must not contain parent traversal or empty path components."
  }
  return $Value.Replace("\", "/")
}

function Resolve-ExistingDirectory {
  param(
    [Parameter(Mandatory)] [string]$Path,
    [Parameter(Mandatory)] [string]$Label
  )

  $resolved = $null
  try {
    $resolved = [System.IO.Path]::GetFullPath($Path)
  }
  catch {
    throw "$Label is not a valid directory path."
  }
  if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
    throw "$Label must already exist as a directory."
  }
  return $resolved
}

function Assert-StageDirectory {
  param([Parameter(Mandatory)] [string]$Path)

  $resolved = Resolve-ExistingDirectory -Path $Path -Label "EvidenceDirectory"
  $directory = [System.IO.DirectoryInfo]$resolved
  $parent = $directory.Parent
  if ($directory.Name -cne "git-safety-stages" -or $null -eq $parent -or $parent.Name -cne "artifacts") {
    throw "EvidenceDirectory must be an existing artifacts\git-safety-stages directory."
  }
  return $resolved
}

function Resolve-OutputPath {
  param(
    [Parameter(Mandatory)] [string]$Path,
    [Parameter(Mandatory)] [string]$ArtifactDirectory
  )

  try {
    $resolved = [System.IO.Path]::GetFullPath($Path)
  }
  catch {
    throw "OutputPath is not a valid file path."
  }
  if ([System.IO.Path]::GetExtension($resolved) -cne ".json") {
    throw "OutputPath must use the .json extension."
  }
  $parentPath = [System.IO.Path]::GetDirectoryName($resolved)
  if ([string]::IsNullOrWhiteSpace($parentPath) -or
    -not (Test-Path -LiteralPath $parentPath -PathType Container)) {
    throw "OutputPath parent must already exist."
  }
  $parent = [System.IO.DirectoryInfo]$parentPath
  $expectedParent = [System.IO.Path]::GetFullPath($ArtifactDirectory)
  if ($parent.Name -cne "artifacts" -or
    -not [string]::Equals($parent.FullName, $expectedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputPath must be directly below the selected artifacts directory."
  }
  if ((Test-Path -LiteralPath $resolved) -and -not $AllowOverwrite) {
    throw "OutputPath already exists; pass -AllowOverwrite only after reviewing it."
  }
  return $resolved
}

function Invoke-GitReadOnly {
  param([Parameter(Mandatory)] [string[]]$Arguments)

  try {
    # Preserve the leading status-column space in porcelain output.  Trimming
    # the left edge would turn an unstaged ` M` entry into a staged-looking
    # `M ` entry and invalidate the stage observation.
    $raw = (& git @Arguments 2>&1 | Out-String).TrimEnd()
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

function Test-GitSucceeded {
  param([Parameter(Mandatory)] [pscustomobject]$Result)

  return $Result.ExitCode -eq 0
}

function Test-GitHasDiff {
  param([Parameter(Mandatory)] [pscustomobject]$Result)

  # git diff --quiet uses exit code 1 to mean that differences exist.
  return $Result.ExitCode -eq 1
}

function Get-StatusEntries {
  param([Parameter(Mandatory)] [AllowEmptyString()] [string]$Output)

  $entries = @{}
  foreach ($line in ([string]$Output -split "`r?`n")) {
    if ([string]::IsNullOrWhiteSpace($line) -or $line.Length -lt 3) {
      continue
    }
    $path = $line.Substring(3).Trim().Trim('"').Replace("\", "/")
    $entries[$path] = $line.Substring(0, 2)
  }
  return $entries
}

function Get-RepoState {
  param([Parameter(Mandatory)] [string]$Repo)

  $prefix = @("-C", $Repo)
  $inside = Invoke-GitReadOnly -Arguments ($prefix + @("rev-parse", "--is-inside-work-tree"))
  $status = Invoke-GitReadOnly -Arguments ($prefix + @("status", "--porcelain=v1"))
  $diff = Invoke-GitReadOnly -Arguments ($prefix + @("diff", "--quiet"))
  $stagedDiff = Invoke-GitReadOnly -Arguments ($prefix + @("diff", "--cached", "--quiet"))
  $head = Invoke-GitReadOnly -Arguments ($prefix + @("rev-parse", "--verify", "HEAD"))
  $branch = Invoke-GitReadOnly -Arguments ($prefix + @("branch", "--show-current"))
  $history = Invoke-GitReadOnly -Arguments ($prefix + @("log", "-1", "--format=%h"))
  $entries = Get-StatusEntries -Output $status.Output
  $branchPassed = (Test-GitSucceeded -Result $branch) -and -not [string]::IsNullOrWhiteSpace([string]$branch.Output)
  $historyPassed = (Test-GitSucceeded -Result $history) -and -not [string]::IsNullOrWhiteSpace([string]$history.Output)
  return [pscustomobject]@{
    Inside = Test-GitSucceeded -Result $inside
    Status = $status
    StatusEntries = $entries
    Clean = [string]::IsNullOrWhiteSpace([string]$status.Output)
    Diff = $diff
    StagedDiff = $stagedDiff
    Head = if (Test-GitSucceeded -Result $head) { [string]$head.Output } else { "" }
    HasHead = Test-GitSucceeded -Result $head
    Branch = $branchPassed
    History = $historyPassed
  }
}

function Test-StatusCode {
  param(
    [Parameter(Mandatory)] [hashtable]$Entries,
    [Parameter(Mandatory)] [string]$Path,
    [Parameter(Mandatory)] [string]$Pattern
  )

  if (-not $Entries.ContainsKey($Path)) {
    return $false
  }
  return [regex]::IsMatch([string]$Entries[$Path], $Pattern)
}

function Test-Ignore {
  param(
    [Parameter(Mandatory)] [string]$Repo,
    [Parameter(Mandatory)] [string]$Path
  )

  $result = Invoke-GitReadOnly -Arguments @("-C", $Repo, "check-ignore", "--quiet", "--", $Path)
  return Test-GitSucceeded -Result $result
}

function Test-Tracked {
  param(
    [Parameter(Mandatory)] [string]$Repo,
    [Parameter(Mandatory)] [string]$Path
  )

  $result = Invoke-GitReadOnly -Arguments @(
    "-C", $Repo, "ls-files", "--error-unmatch", "--", $Path
  )
  return Test-GitSucceeded -Result $result
}

function New-ObservationMap {
  param([Parameter(Mandatory)] [string[]]$Keys)

  $observations = [ordered]@{}
  foreach ($key in $Keys) {
    $observations[$key] = $false
  }
  return $observations
}

function Read-StageRecords {
  param([Parameter(Mandatory)] [string]$Directory)

  $files = @(Get-ChildItem -LiteralPath $Directory -Filter "*.json" -File | Sort-Object Name)
  $records = [System.Collections.Generic.List[object]]::new()
  foreach ($file in $files) {
    try {
      $record = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
    }
    catch {
      throw "Stage record is not valid JSON."
    }
    if ($record.lesson_id -ne "t06-git-safety" -or $record.trace_version -ne "1") {
      throw "Stage record has an unexpected lesson or trace version."
    }
    $records.Add($record)
  }
  return @($records)
}

function Write-StageRecord {
  param(
    [Parameter(Mandatory)] [string]$Directory,
    [Parameter(Mandatory)] [pscustomobject]$Record,
    [Parameter(Mandatory)] [int]$Sequence
  )

  $target = Join-Path $Directory ("{0:D2}-{1}.json" -f $Sequence, $Record.stage)
  if ((Test-Path -LiteralPath $target) -and -not $AllowOverwrite) {
    throw "Stage record already exists; pass -AllowOverwrite only after reviewing it."
  }
  $encoded = $Record | ConvertTo-Json -Depth 6
  $temporary = Join-Path $Directory ("." + [System.IO.Path]::GetRandomFileName())
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  try {
    [System.IO.File]::WriteAllText($temporary, $encoded, $utf8)
    [System.IO.File]::Move($temporary, $target, $true)
  }
  finally {
    if ([System.IO.File]::Exists($temporary)) {
      [System.IO.File]::Delete($temporary)
    }
  }
}

function Write-OutputJson {
  param(
    [Parameter(Mandatory)] [string]$Target,
    [Parameter(Mandatory)] [string]$Encoded
  )

  $temporary = Join-Path ([System.IO.Path]::GetDirectoryName($Target)) (
    "." + [System.IO.Path]::GetRandomFileName()
  )
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  try {
    [System.IO.File]::WriteAllText($temporary, $Encoded, $utf8)
    [System.IO.File]::Move($temporary, $Target, $true)
  }
  finally {
    if ([System.IO.File]::Exists($temporary)) {
      [System.IO.File]::Delete($temporary)
    }
  }
}

if (-not $ReadOnlyConfirmed) {
  throw "Pass -ReadOnlyConfirmed after confirming this script will inspect only the selected disposable repository."
}

$repo = Resolve-ExistingDirectory -Path $RepoPath -Label "RepoPath"
$stageDirectory = Assert-StageDirectory -Path $EvidenceDirectory
$secret = Assert-RelativePath -Value $SecretPath -Label "SecretPath"
$trackedPath = Assert-RelativePath -Value $TrackedExercisePath -Label "TrackedExercisePath"
$untrackedPath = Assert-RelativePath -Value $UntrackedExercisePath -Label "UntrackedExercisePath"
if ($Stage -ne "final" -and -not [string]::IsNullOrWhiteSpace($OutputPath)) {
  throw "OutputPath is allowed only for the final stage."
}
if ($Stage -eq "final" -and -not [string]::IsNullOrWhiteSpace($OutputPath)) {
  $artifactDirectory = ([System.IO.DirectoryInfo]$stageDirectory).Parent.FullName
  $safeOutput = Resolve-OutputPath -Path $OutputPath -ArtifactDirectory $artifactDirectory
}

$stageIndex = [array]::IndexOf($stageOrder, $Stage)
$recordsBefore = @(Read-StageRecords -Directory $stageDirectory)
$expectedPriorCount = $stageIndex
if ($Stage -eq "final" -and $recordsBefore.Count -eq $stageOrder.Count) {
  $lastRecord = $recordsBefore[$recordsBefore.Count - 1]
  if ($lastRecord.stage -ne "final" -or $lastRecord.sequence -ne $stageOrder.Count) {
    throw "Stage records are missing or out of order."
  }
  if (-not $AllowOverwrite) {
    throw "Final stage record already exists; pass -AllowOverwrite only after reviewing it."
  }
  $recordsBefore = @($recordsBefore | Select-Object -First $stageIndex)
}
if ($recordsBefore.Count -ne $expectedPriorCount) {
  throw "Stage records must be completed in order; expected $expectedPriorCount prior records."
}
for ($index = 0; $index -lt $recordsBefore.Count; $index++) {
  if ($recordsBefore[$index].stage -ne $stageOrder[$index] -or
    $recordsBefore[$index].sequence -ne ($index + 1)) {
    throw "Stage records are missing or out of order."
  }
}
$traceId = if ($recordsBefore.Count -eq 0) {
  [guid]::NewGuid().ToString("N")
}
else {
  [string]$recordsBefore[0].trace_id
}
if ([string]::IsNullOrWhiteSpace($traceId)) {
  throw "Stage trace does not have a valid trace id."
}

$state = Get-RepoState -Repo $repo
$prefix = @("-C", $repo)
$observations = switch ($Stage) {
  "baseline" {
    $map = New-ObservationMap -Keys @("repo", "clean", "head", "branch", "history")
    $map.repo = $state.Inside
    $map.clean = $state.Clean
    $map.head = $state.HasHead
    $map.branch = $state.Branch
    $map.history = $state.History
    $map
  }
  "branch-history" {
    $map = New-ObservationMap -Keys @("branch", "history")
    $map.branch = $state.Branch
    $map.history = $state.History
    $map
  }
  "change-created" {
    $map = New-ObservationMap -Keys @("tracked_change", "untracked_change", "diff")
    $map.tracked_change = Test-StatusCode -Entries $state.StatusEntries -Path $trackedPath -Pattern "^ M$"
    $map.untracked_change = Test-StatusCode -Entries $state.StatusEntries -Path $untrackedPath -Pattern "^\?\?$"
    $map.diff = Test-GitHasDiff -Result $state.Diff
    $map
  }
  "selective-stage" {
    $map = New-ObservationMap -Keys @("staged_change", "unstaged_change", "staged_diff", "diff")
    $map.staged_change = Test-StatusCode -Entries $state.StatusEntries -Path $trackedPath -Pattern "^[AMRC][M ]$"
    $map.unstaged_change = Test-StatusCode -Entries $state.StatusEntries -Path $untrackedPath -Pattern "^\?\?$"
    $map.staged_diff = Test-GitHasDiff -Result $state.StagedDiff
    $map.diff = (Test-GitHasDiff -Result $state.Diff) -or $map.unstaged_change
    $map
  }
  "first-commit-decision" {
    $map = New-ObservationMap -Keys @("staged_change", "secret_untracked", "approval")
    $map.staged_change = Test-StatusCode -Entries $state.StatusEntries -Path $trackedPath -Pattern "^[AMRC][M ]$"
    $map.secret_untracked = -not (Test-Tracked -Repo $repo -Path $secret)
    $map.approval = [bool]$HumanApproved
    $map
  }
  "first-commit-recorded" {
    $prior = $recordsBefore[$stageIndex - 1]
    $map = New-ObservationMap -Keys @("head_changed", "clean")
    $map.head_changed = $state.HasHead -and [string]$state.Head -ne [string]$prior.internal.head
    $map.clean = $state.Clean
    $map
  }
  "secret-before" {
    $map = New-ObservationMap -Keys @("secret_absent", "ignore_absent")
    $map.secret_absent = -not (Test-Path -LiteralPath (Join-Path $repo $secret) -PathType Leaf)
    $map.ignore_absent = -not (Test-Ignore -Repo $repo -Path $secret)
    $map
  }
  "secret-ignored" {
    $map = New-ObservationMap -Keys @("secret_present", "ignored", "untracked", "ignore_unstaged")
    $secretAbsolute = Join-Path $repo $secret
    $map.secret_present = Test-Path -LiteralPath $secretAbsolute -PathType Leaf
    $map.ignored = Test-Ignore -Repo $repo -Path $secret
    $map.untracked = -not (Test-Tracked -Repo $repo -Path $secret)
    $map.ignore_unstaged = Test-StatusCode -Entries $state.StatusEntries -Path ".gitignore" -Pattern "^\?\?$"
    $map
  }
  "secret-commit-decision" {
    $map = New-ObservationMap -Keys @("staged_ignore", "secret_untracked", "approval")
    $map.staged_ignore = Test-StatusCode -Entries $state.StatusEntries -Path ".gitignore" -Pattern "^[AMRC][M ]$"
    $map.secret_untracked = -not (Test-Tracked -Repo $repo -Path $secret)
    $map.approval = [bool]$HumanApproved
    $map
  }
  "secret-commit-recorded" {
    $prior = $recordsBefore[$stageIndex - 1]
    $map = New-ObservationMap -Keys @("head_changed", "clean")
    $map.head_changed = $state.HasHead -and [string]$state.Head -ne [string]$prior.internal.head
    $map.clean = $state.Clean
    $map
  }
  "recovery-before" {
    $map = New-ObservationMap -Keys @("tracked_change", "diff")
    $map.tracked_change = Test-StatusCode -Entries $state.StatusEntries -Path $trackedPath -Pattern "^ M$"
    $map.diff = Test-GitHasDiff -Result $state.Diff
    $map
  }
  "recovery-recorded" {
    $map = New-ObservationMap -Keys @("clean", "matches_head")
    $readmeAtHead = Invoke-GitReadOnly -Arguments ($prefix + @("diff", "--quiet", "HEAD", "--", $trackedPath))
    $map.clean = $state.Clean
    $map.matches_head = Test-GitSucceeded -Result $readmeAtHead
    $map
  }
  "final" {
    $map = New-ObservationMap -Keys @("clean", "secret_untracked")
    $map.clean = $state.Clean
    $map.secret_untracked = -not (Test-Tracked -Repo $repo -Path $secret)
    $map
  }
}

$result = if (@($observations.Values) -contains $false) { "failed" } else { "passed" }
$record = [ordered]@{
  lesson_id = "t06-git-safety"
  trace_version = "1"
  trace_id = $traceId
  stage = $Stage
  sequence = $stageIndex + 1
  result = $result
  observations = $observations
  internal = [ordered]@{
    head = $state.Head
  }
}
$recordObject = [pscustomobject]$record
Write-StageRecord -Directory $stageDirectory -Record $recordObject -Sequence ($stageIndex + 1)

if ($Stage -ne "final") {
  [ordered]@{
    lesson_id = "t06-git-safety"
    stage = $Stage
    result = $result
  } | ConvertTo-Json -Compress
  exit 0
}

$allRecords = @(Read-StageRecords -Directory $stageDirectory)
if ($allRecords.Count -ne $stageOrder.Count) {
  throw "The final stage requires the complete ordered journey."
}
$publicStages = @(
  foreach ($item in $allRecords) {
    [ordered]@{
      id = [string]$item.stage
      sequence = [int]$item.sequence
      result = [string]$item.result
      observations = $item.observations
    }
  }
)
$stagePassed = @{}
foreach ($item in $allRecords) {
  $stagePassed[[string]$item.stage] = [string]$item.result -eq "passed"
}
$checks = @(
  [ordered]@{ id = "status-baseline"; result = if ($stagePassed["baseline"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "diff-reviewed"; result = if ($stagePassed["change-created"] -and $stagePassed["selective-stage"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "selective-stage"; result = if ($stagePassed["selective-stage"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "intentional-commit"; result = if ($stagePassed["first-commit-decision"] -and $stagePassed["first-commit-recorded"] -and $stagePassed["secret-commit-decision"] -and $stagePassed["secret-commit-recorded"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "branch-inspected"; result = if ($stagePassed["branch-history"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "history-inspected"; result = if ($stagePassed["branch-history"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "secret-ignored"; result = if ($stagePassed["secret-before"] -and $stagePassed["secret-ignored"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "recovery-complete"; result = if ($stagePassed["recovery-before"] -and $stagePassed["recovery-recorded"] -and $stagePassed["final"]) { "passed" } else { "failed" } }
)
$diagnostic = [ordered]@{
  lesson_id = "t06-git-safety"
  platform = if ($IsWindows) { "windows" } elseif ($IsMacOS) { "macos" } elseif ($IsLinux) { "linux" } else { "unknown" }
  shell = "powershell"
  journey = [ordered]@{
    trace_version = "1"
    trace_id = $traceId
    stages = $publicStages
  }
  checks = $checks
}
$encoded = $diagnostic | ConvertTo-Json -Depth 8
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $encoded
  exit 0
}
Write-OutputJson -Target $safeOutput -Encoded $encoded
