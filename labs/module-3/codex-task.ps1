<#!
.SYNOPSIS
  Record the ordered, privacy-safe evidence for the Codex repository task.

.DESCRIPTION
  The script only inspects the explicitly selected disposable repository and
  writes status-only stage records below its ignored artifacts directory.  It
  never calls Codex, the OpenAI API, a remote, or a real device.  A learner may
  use Codex in the selected directory between checkpoints; the resulting
  evidence does not claim that a live Codex call happened.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$RepoPath,
  [Parameter(Mandatory)]
  [ValidateSet("baseline", "clarify", "plan", "failure-observed", "change", "recovery", "review", "delivery")]
  [string]$Stage,
  [string]$EvidenceDirectory,
  [string]$OutputPath,
  [string]$CourseVersion = "0.1.0-alpha",
  [switch]$HumanApproved,
  [switch]$AllowOverwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stageOrder = @(
  "baseline",
  "clarify",
  "plan",
  "failure-observed",
  "change",
  "recovery",
  "review",
  "delivery"
)
$allowedChangedPaths = @(
  "src/telemetry_report.py",
  "worklog/clarification.md",
  "worklog/plan.md",
  "worklog/recovery.md",
  "worklog/handoff.md"
)

function Invoke-NativeResult {
  param(
    [Parameter(Mandatory)] [string]$File,
    [Parameter(Mandatory)] [string[]]$Arguments,
    [string]$WorkingDirectory
  )

  try {
    if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
      $output = (& $File @Arguments 2>&1 | Out-String).TrimEnd()
    }
    else {
      Push-Location -LiteralPath $WorkingDirectory
      try {
        $output = (& $File @Arguments 2>&1 | Out-String).TrimEnd()
      }
      finally {
        Pop-Location
      }
    }
    $exitCode = $LASTEXITCODE
  }
  catch {
    return [pscustomobject]@{ ExitCode = 127; Output = "" }
  }
  return [pscustomobject]@{ ExitCode = $exitCode; Output = $output }
}

function Resolve-Directory {
  param([Parameter(Mandatory)] [string]$Path, [Parameter(Mandatory)] [string]$Label)
  try { $resolved = [System.IO.Path]::GetFullPath($Path) }
  catch { throw "$Label is not a valid path." }
  if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
    throw "$Label must already exist as a directory."
  }
  return $resolved
}

function Assert-StageDirectory {
  param([Parameter(Mandatory)] [string]$Path)
  $resolved = Resolve-Directory -Path $Path -Label "EvidenceDirectory"
  $directory = [System.IO.DirectoryInfo]$resolved
  $parent = $directory.Parent
  if ($directory.Name -cne "codex-task-stages" -or $null -eq $parent -or $parent.Name -cne "artifacts") {
    throw "EvidenceDirectory must be an existing artifacts\codex-task-stages directory."
  }
  return $resolved
}

function Assert-OutputPath {
  param([Parameter(Mandatory)] [string]$Path, [Parameter(Mandatory)] [string]$ArtifactDirectory)
  try { $resolved = [System.IO.Path]::GetFullPath($Path) }
  catch { throw "OutputPath is not a valid path." }
  if ([System.IO.Path]::GetExtension($resolved) -cne ".json") {
    throw "OutputPath must use the .json extension."
  }
  $parent = [System.IO.Path]::GetDirectoryName($resolved)
  $expected = [System.IO.Path]::GetFullPath($ArtifactDirectory)
  if ([string]::IsNullOrWhiteSpace($parent) -or
      -not [string]::Equals([System.IO.Path]::GetFullPath($parent), $expected, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "OutputPath must be directly below the selected artifacts directory."
  }
  if ((Test-Path -LiteralPath $resolved) -and -not $AllowOverwrite) {
    throw "OutputPath already exists; pass -AllowOverwrite only after reviewing it."
  }
  return $resolved
}

function Invoke-Git {
  param([Parameter(Mandatory)] [string]$Repo, [Parameter(Mandatory)] [string[]]$Arguments)
  return Invoke-NativeResult -File "git" -Arguments (@("-C", $Repo) + $Arguments)
}

function Get-ChangedPaths {
  param([Parameter(Mandatory)] [string]$Repo)
  $names = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($gitArguments in @(
    @("diff", "--name-only"),
    @("diff", "--cached", "--name-only"),
    @("ls-files", "--others", "--exclude-standard")
  )) {
    $result = Invoke-Git -Repo $Repo -Arguments $gitArguments
    if ($result.ExitCode -ne 0) { continue }
    foreach ($line in ([string]$result.Output -split "`r?`n")) {
      if (-not [string]::IsNullOrWhiteSpace($line)) {
        $normalized = $line.Trim().Replace("\", "/")
        if ($normalized -match "^(?i:warning|fatal):") { continue }
        [void]$names.Add($normalized)
      }
    }
  }
  return @($names | Sort-Object)
}

function Test-CompleteNote {
  param(
    [Parameter(Mandatory)] [string]$Path,
    [Parameter(Mandatory)] [string[]]$Headings
  )
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
  $text = Get-Content -LiteralPath $Path -Raw
  if ($text -match "待学员") { return $false }
  foreach ($heading in $Headings) {
    if ($text -notmatch ("(?im)^##\s+" + [regex]::Escape($heading) + "\s*$")) { return $false }
  }
  return $true
}

function Get-TestRun {
  param([Parameter(Mandatory)] [string]$Repo)
  return Invoke-NativeResult -File "python" -Arguments @("-m", "unittest", "discover", "-s", "tests", "-v") -WorkingDirectory $Repo
}

function Get-ReportRun {
  param([Parameter(Mandatory)] [string]$Repo)
  $artifactDirectory = Join-Path $Repo "artifacts"
  New-Item -ItemType Directory -Path $artifactDirectory -Force | Out-Null
  return Invoke-NativeResult -File "python" -Arguments @(
    "-m", "telemetry_report", "--input", "data/readings.csv", "--output", "artifacts/report.json"
  ) -WorkingDirectory $Repo
}

function Test-Report {
  param([Parameter(Mandatory)] [string]$Repo)
  $path = Join-Path $Repo "artifacts\report.json"
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
  try { $report = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
  catch { return $false }
  if ($report.schema -ne "telemetry-report-v1" -or
      $report.valid_count -ne 3 -or
      $report.mean_celsius -ne 20.333 -or
      $report.unit -ne "C") { return $false }
  $encoded = $report | ConvertTo-Json -Depth 6 -Compress
  return $encoded -notmatch "timestamp|rows|not-a-timestamp"
}

function Test-AllowedScope {
  param([Parameter(Mandatory)] [string[]]$Paths)
  foreach ($path in $Paths) {
    if ($allowedChangedPaths -notcontains $path) { return $false }
  }
  return $true
}

function New-ObservationMap {
  param([Parameter(Mandatory)] [string[]]$Keys)
  $map = [ordered]@{}
  foreach ($key in $Keys) { $map[$key] = $false }
  return $map
}

function Read-Records {
  param([Parameter(Mandatory)] [string]$Directory)
  $records = @()
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter "*.json" -File | Sort-Object Name)) {
    try { $record = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json }
    catch { throw "Stage record is not valid JSON." }
    if ($record.lesson_id -ne "t04-codex-repository-task" -or $record.trace_version -ne "1") {
      throw "Stage record has an unexpected lesson or trace version."
    }
    $records += $record
  }
  return @($records)
}

function Write-JsonFile {
  param([Parameter(Mandatory)] [string]$Path, [Parameter(Mandatory)] [string]$Value)
  $temporary = Join-Path ([System.IO.Path]::GetDirectoryName($Path)) ("." + [System.IO.Path]::GetRandomFileName())
  $utf8 = [System.Text.UTF8Encoding]::new($false)
  try {
    [System.IO.File]::WriteAllText($temporary, $Value, $utf8)
    [System.IO.File]::Move($temporary, $Path, $true)
  }
  finally {
    if ([System.IO.File]::Exists($temporary)) { [System.IO.File]::Delete($temporary) }
  }
}

function Get-Result {
  param([Parameter(Mandatory)] [System.Collections.IDictionary]$Observations)
  if (@($Observations.Values) -contains $false) { return "failed" }
  return "passed"
}

if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
  $EvidenceDirectory = Join-Path (Join-Path $RepoPath "artifacts") "codex-task-stages"
}
$repo = Resolve-Directory -Path $RepoPath -Label "RepoPath"
$stageDirectory = Assert-StageDirectory -Path $EvidenceDirectory
$artifactDirectory = ([System.IO.DirectoryInfo]$stageDirectory).Parent.FullName
if ($Stage -eq "delivery") {
  if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $artifactDirectory "t04-codex-repository-task-evidence.json"
  }
  $safeOutput = Assert-OutputPath -Path $OutputPath -ArtifactDirectory $artifactDirectory
}
elseif (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
  throw "OutputPath is allowed only for the delivery stage."
}

$stageIndex = [array]::IndexOf($stageOrder, $Stage)
$recordsBefore = @(Read-Records -Directory $stageDirectory)
if ($recordsBefore.Count -ne $stageIndex) {
  throw "Stage records must be completed in order; expected $stageIndex prior records."
}
for ($index = 0; $index -lt $recordsBefore.Count; $index++) {
  if ($recordsBefore[$index].stage -ne $stageOrder[$index] -or $recordsBefore[$index].sequence -ne ($index + 1)) {
    throw "Stage records are missing or out of order."
  }
}
$traceId = if ($recordsBefore.Count -eq 0) { [guid]::NewGuid().ToString("N") } else { [string]$recordsBefore[0].trace_id }
$status = Invoke-Git -Repo $repo -Arguments @("status", "--porcelain=v1", "--untracked-files=all")
$branch = Invoke-Git -Repo $repo -Arguments @("branch", "--show-current")
$head = Invoke-Git -Repo $repo -Arguments @("rev-parse", "--verify", "HEAD")
$changedPaths = Get-ChangedPaths -Repo $repo
$observations = switch ($Stage) {
  "baseline" {
    $map = New-ObservationMap -Keys @("repo", "clean", "head", "branch")
    $map.repo = (Invoke-Git -Repo $repo -Arguments @("rev-parse", "--is-inside-work-tree")).ExitCode -eq 0
    $map.clean = [string]::IsNullOrWhiteSpace([string]$status.Output)
    $map.head = $head.ExitCode -eq 0
    $map.branch = $branch.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace([string]$branch.Output)
    $map
  }
  "clarify" {
    $map = New-ObservationMap -Keys @("goal", "non_goal", "acceptance")
    $map.goal = Test-CompleteNote -Path (Join-Path $repo "worklog\clarification.md") -Headings @("Goal")
    $map.non_goal = Test-CompleteNote -Path (Join-Path $repo "worklog\clarification.md") -Headings @("Non-goals")
    $map.acceptance = Test-CompleteNote -Path (Join-Path $repo "worklog\clarification.md") -Headings @("Acceptance")
    $map
  }
  "plan" {
    $map = New-ObservationMap -Keys @("files", "commands", "permissions", "stop", "approval")
    $plan = Join-Path $repo "worklog\plan.md"
    $map.files = Test-CompleteNote -Path $plan -Headings @("Files")
    $map.commands = Test-CompleteNote -Path $plan -Headings @("Commands")
    $map.permissions = Test-CompleteNote -Path $plan -Headings @("Permissions")
    $map.stop = Test-CompleteNote -Path $plan -Headings @("Stop")
    $map.approval = [bool]$HumanApproved
    $map
  }
  "failure-observed" {
    $map = New-ObservationMap -Keys @("expected_failure", "error_classified")
    $test = Get-TestRun -Repo $repo
    $map.expected_failure = $test.ExitCode -ne 0
    $map.error_classified = [regex]::IsMatch([string]$test.Output, "(?i)fail|assert|error")
    $map
  }
  "change" {
    $map = New-ObservationMap -Keys @("source_changed", "diff", "approval")
    $map.source_changed = $changedPaths -contains "src/telemetry_report.py"
    $diff = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--quiet")
    $map.diff = $diff.ExitCode -eq 1
    $map.approval = [bool]$HumanApproved
    $map
  }
  "recovery" {
    $map = New-ObservationMap -Keys @("tests_passed", "report_generated")
    $tests = Get-TestRun -Repo $repo
    $reportRun = Get-ReportRun -Repo $repo
    $map.tests_passed = $tests.ExitCode -eq 0
    $map.report_generated = $reportRun.ExitCode -eq 0 -and (Test-Report -Repo $repo)
    $map
  }
  "review" {
    $map = New-ObservationMap -Keys @("diff_reviewed", "scope_clean", "no_secrets")
    $diffCheck = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--check")
    $diffText = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--")
    $map.diff_reviewed = $diffCheck.ExitCode -eq 0
    $map.scope_clean = Test-AllowedScope -Paths $changedPaths
    $map.no_secrets = -not [regex]::IsMatch([string]$diffText.Output, "(?i)api[_-]?key|sk-[A-Za-z0-9]|password\s*=|token\s*=")
    $map
  }
  "delivery" {
    $map = New-ObservationMap -Keys @("handoff", "evidence_ready", "human_approved")
    $map.handoff = Test-CompleteNote -Path (Join-Path $repo "worklog\handoff.md") -Headings @("Diff", "Verification", "Decision")
    $map.evidence_ready = (Test-Path -LiteralPath (Join-Path $repo "artifacts\report.json") -PathType Leaf) -and ($recordsBefore.Count -eq 7)
    $map.human_approved = [bool]$HumanApproved
    $map
  }
}

$result = Get-Result -Observations $observations
$record = [ordered]@{
  lesson_id = "t04-codex-repository-task"
  trace_version = "1"
  trace_id = $traceId
  stage = $Stage
  sequence = $stageIndex + 1
  result = $result
  observations = $observations
}
$recordPath = Join-Path $stageDirectory ("{0:D2}-{1}.json" -f ($stageIndex + 1), $Stage)
if ((Test-Path -LiteralPath $recordPath) -and -not $AllowOverwrite) {
  throw "Stage record already exists; pass -AllowOverwrite only after reviewing it."
}
Write-JsonFile -Path $recordPath -Value (($record | ConvertTo-Json -Depth 8) + "`n")

if ($Stage -ne "delivery") {
  [ordered]@{ lesson_id = "t04-codex-repository-task"; stage = $Stage; result = $result } | ConvertTo-Json -Compress
  exit 0
}

$allRecords = @(Read-Records -Directory $stageDirectory)
if ($allRecords.Count -ne $stageOrder.Count) { throw "The delivery stage requires the complete ordered journey." }
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
foreach ($item in $allRecords) { $stagePassed[[string]$item.stage] = [string]$item.result -eq "passed" }
$checks = @(
  [ordered]@{ id = "clarification-recorded"; result = if ($stagePassed["clarify"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "plan-recorded"; result = if ($stagePassed["plan"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "failure-recovered"; result = if ($stagePassed["failure-observed"] -and $stagePassed["recovery"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "scoped-change"; result = if ($stagePassed["change"] -and $stagePassed["review"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "tests-passed"; result = if ($stagePassed["recovery"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "diff-reviewed"; result = if ($stagePassed["review"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "report-generated"; result = if ($stagePassed["recovery"] -and $stagePassed["delivery"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "delivery-recorded"; result = if ($stagePassed["delivery"]) { "passed" } else { "failed" } }
)
$resultValues = @($checks | ForEach-Object { [string]$_.result })
$documentResult = if (@($resultValues | Where-Object { $_ -ne "passed" }).Count -eq 0) { "passed" } elseif (@($resultValues | Where-Object { $_ -eq "passed" }).Count -eq 0) { "failed" } else { "partial" }
$summary = @{
  passed = "所有必需证据均已通过。"
  partial = "部分证据已通过，仍有证据需要补齐。"
  failed = "证据未通过，请根据本地检查结果恢复后重试。"
}[$documentResult]
$document = [ordered]@{
  contract = "agent-engineering-course/evidence"
  contract_version = "1"
  course_version = $CourseVersion
  lesson_id = "t04-codex-repository-task"
  task_id = "telemetry-report-v1"
  platform = "windows"
  shell = "powershell"
  result = $documentResult
  anonymous = $true
  checked_on = (Get-Date).ToString("yyyy-MM-dd")
  summary = $summary
  evidence = $checks
  journey = [ordered]@{
    trace_version = "1"
    trace_id = $traceId
    stages = $publicStages
  }
  artifact = [ordered]@{
    version = "1"
    report = if ($stagePassed["recovery"]) { "passed" } else { "failed" }
    tests = if ($stagePassed["recovery"]) { "passed" } else { "failed" }
    delivery = if ($stagePassed["delivery"]) { "passed" } else { "failed" }
  }
}
Write-JsonFile -Path $safeOutput -Value (($document | ConvertTo-Json -Depth 10) + "`n")
[ordered]@{ lesson_id = "t04-codex-repository-task"; result = $documentResult; output = "anonymous-evidence" } | ConvertTo-Json -Compress
