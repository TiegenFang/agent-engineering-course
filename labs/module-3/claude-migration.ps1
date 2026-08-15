<#
.SYNOPSIS
  Record privacy-safe evidence for the Claude Code migration challenge.

.DESCRIPTION
  The script only inspects the explicitly selected disposable repository and
  writes status-only stage records below its ignored artifacts directory.  It
  never calls Claude Code, Codex, an API, a remote, or a real device.  A learner
  may use Claude Code in the selected directory between checkpoints; evidence
  keeps that live-call status as not verified unless a human records it outside
  this contract.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)]
  [string]$RepoPath,
  [Parameter(Mandatory)]
  [ValidateSet("baseline", "clarify", "plan", "official-facts", "failure-observed", "change", "recovery", "review", "delivery")]
  [string]$Stage,
  [ValidateSet("claude-only", "dual-tool")]
  [string]$PathMode = "claude-only",
  [string]$EvidenceDirectory,
  [string]$OutputPath,
  [string]$CourseVersion = "1.0.0",
  [switch]$HumanApproved,
  [switch]$AllowOverwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stageOrder = @(
  "baseline",
  "clarify",
  "plan",
  "official-facts",
  "failure-observed",
  "change",
  "recovery",
  "review",
  "delivery"
)
$allowedChangedPaths = @(
  "src/pressure_report.py",
  "worklog/clarification.md",
  "worklog/plan.md",
  "worklog/official-sources.md",
  "worklog/claude-only.md",
  "worklog/codex-reference.md",
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
      try { $output = (& $File @Arguments 2>&1 | Out-String).TrimEnd() }
      finally { Pop-Location }
    }
    $exitCode = $LASTEXITCODE
  }
  catch { return [pscustomobject]@{ ExitCode = 127; Output = "" } }
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
  if ($directory.Name -cne "claude-migration-stages" -or $null -eq $parent -or $parent.Name -cne "artifacts") {
    throw "EvidenceDirectory must be an existing artifacts\claude-migration-stages directory."
  }
  return $resolved
}

function Assert-OutputPath {
  param([Parameter(Mandatory)] [string]$Path, [Parameter(Mandatory)] [string]$ArtifactDirectory)
  try { $resolved = [System.IO.Path]::GetFullPath($Path) }
  catch { throw "OutputPath is not a valid path." }
  if ([System.IO.Path]::GetExtension($resolved) -cne ".json") { throw "OutputPath must use the .json extension." }
  $parent = [System.IO.Path]::GetDirectoryName($resolved)
  if ([string]::IsNullOrWhiteSpace($parent) -or
      -not [string]::Equals([System.IO.Path]::GetFullPath($parent), [System.IO.Path]::GetFullPath($ArtifactDirectory), [System.StringComparison]::OrdinalIgnoreCase)) {
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
  foreach ($args in @(
    @("diff", "--name-only"),
    @("diff", "--cached", "--name-only"),
    @("ls-files", "--others", "--exclude-standard")
  )) {
    $result = Invoke-Git -Repo $Repo -Arguments $args
    if ($result.ExitCode -ne 0) { continue }
    foreach ($line in ([string]$result.Output -split "`r?`n")) {
      $candidate = $line.Trim()
      if (-not [string]::IsNullOrWhiteSpace($candidate) -and $candidate -notmatch "(?i)^(warning|hint):") {
        [void]$names.Add($candidate.Replace("\", "/"))
      }
    }
  }
  return @($names | Sort-Object)
}

function Test-CompleteNote {
  param([Parameter(Mandatory)] [string]$Path, [Parameter(Mandatory)] [string[]]$Headings)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
  $text = Get-Content -LiteralPath $Path -Raw
  if ($text -match "(?i)待学员|待填写|TODO|FIXME") { return $false }
  foreach ($heading in $Headings) {
    if ($text -notmatch ("(?im)^##\s+" + [regex]::Escape($heading) + "\s*$")) { return $false }
  }
  return $true
}

function Test-OfficialNotes {
  param([Parameter(Mandatory)] [string]$Path)
  if (-not (Test-CompleteNote -Path $Path -Headings @("Installation", "Operation", "Permissions", "Cost", "Verification boundary"))) { return $false }
  $text = Get-Content -LiteralPath $Path -Raw
  foreach ($url in @(
    "https://code.claude.com/docs/en/installation",
    "https://code.claude.com/docs/en/common-workflows",
    "https://code.claude.com/docs/en/permissions",
    "https://code.claude.com/docs/en/costs"
  )) { if ($text -notmatch [regex]::Escape($url)) { return $false } }
  return $text -match "2026-08-13" -and $text -match "(?i)not.*verified|未验证|未完成"
}

function Test-PathNote {
  param([Parameter(Mandatory)] [string]$Repo, [Parameter(Mandatory)] [string]$Mode)
  $claude = Test-CompleteNote -Path (Join-Path $Repo "worklog\claude-only.md") -Headings @("Path", "Evidence", "No live call claim")
  if ($Mode -eq "claude-only") { return $claude }
  $codex = Test-CompleteNote -Path (Join-Path $Repo "worklog\codex-reference.md") -Headings @("Codex reference", "Changed input", "No live call claim")
  return $claude -and $codex
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
    "-m", "pressure_report", "--input", "data/readings.csv", "--output", "artifacts/report.json"
  ) -WorkingDirectory $Repo
}

function Test-Report {
  param([Parameter(Mandatory)] [string]$Repo)
  $path = Join-Path $Repo "artifacts\report.json"
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $false }
  try { $report = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json }
  catch { return $false }
  if ($report.schema -ne "pressure-report-v1" -or
      $report.valid_count -ne 3 -or
      $report.mean_kpa -ne 101.317 -or
      $report.peak_kpa -ne 101.325 -or
      $report.alarm_count -ne 2 -or
      $report.unit -ne "kPa") { return $false }
  $encoded = $report | ConvertTo-Json -Depth 6 -Compress
  return $encoded -notmatch "timestamp|rows|not-a-timestamp"
}

function Test-AllowedScope {
  param([Parameter(Mandatory)] [string[]]$Paths)
  foreach ($path in $Paths) { if ($allowedChangedPaths -notcontains $path) { return $false } }
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
    if ($record.lesson_id -ne "t04-claude-migration" -or $record.trace_version -ne "1") {
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
  finally { if ([System.IO.File]::Exists($temporary)) { [System.IO.File]::Delete($temporary) } }
}

function Get-Result {
  param([Parameter(Mandatory)] [System.Collections.IDictionary]$Observations)
  if (@($Observations.Values) -contains $false) { return "failed" }
  return "passed"
}

if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
  $EvidenceDirectory = Join-Path (Join-Path $RepoPath "artifacts") "claude-migration-stages"
}
$repo = Resolve-Directory -Path $RepoPath -Label "RepoPath"
$stageDirectory = Assert-StageDirectory -Path $EvidenceDirectory
$artifactDirectory = ([System.IO.DirectoryInfo]$stageDirectory).Parent.FullName
if ($Stage -eq "delivery") {
  if ([string]::IsNullOrWhiteSpace($OutputPath)) { $OutputPath = Join-Path $artifactDirectory "t04-claude-migration-evidence.json" }
  $safeOutput = Assert-OutputPath -Path $OutputPath -ArtifactDirectory $artifactDirectory
}
elseif (-not [string]::IsNullOrWhiteSpace($OutputPath)) { throw "OutputPath is allowed only for the delivery stage." }

$stageIndex = [array]::IndexOf($stageOrder, $Stage)
$recordsBefore = @(Read-Records -Directory $stageDirectory)
if ($recordsBefore.Count -ne $stageIndex) { throw "Stage records must be completed in order; expected $stageIndex prior records." }
for ($index = 0; $index -lt $recordsBefore.Count; $index++) {
  if ($recordsBefore[$index].stage -ne $stageOrder[$index] -or $recordsBefore[$index].sequence -ne ($index + 1)) { throw "Stage records are missing or out of order." }
}
$traceId = if ($recordsBefore.Count -eq 0) { [guid]::NewGuid().ToString("N") } else { [string]$recordsBefore[0].trace_id }
$status = Invoke-Git -Repo $repo -Arguments @("status", "--porcelain=v1", "--untracked-files=all")
$branch = Invoke-Git -Repo $repo -Arguments @("branch", "--show-current")
$head = Invoke-Git -Repo $repo -Arguments @("rev-parse", "--verify", "HEAD")
$changedPaths = Get-ChangedPaths -Repo $repo
$observations = switch ($Stage) {
  "baseline" {
    $map = New-ObservationMap -Keys @("repo", "clean", "head", "branch", "path_declared")
    $map.repo = (Invoke-Git -Repo $repo -Arguments @("rev-parse", "--is-inside-work-tree")).ExitCode -eq 0
    $map.clean = [string]::IsNullOrWhiteSpace([string]$status.Output)
    $map.head = $head.ExitCode -eq 0
    $map.branch = $branch.ExitCode -eq 0 -and -not [string]::IsNullOrWhiteSpace([string]$branch.Output)
    $map.path_declared = Test-PathNote -Repo $repo -Mode $PathMode
    $map
  }
  "clarify" {
    $map = New-ObservationMap -Keys @("goal", "non_goal", "acceptance", "migration")
    $note = Join-Path $repo "worklog\clarification.md"
    $map.goal = Test-CompleteNote -Path $note -Headings @("Goal")
    $map.non_goal = Test-CompleteNote -Path $note -Headings @("Non-goals")
    $map.acceptance = Test-CompleteNote -Path $note -Headings @("Acceptance")
    $map.migration = (Test-CompleteNote -Path $note -Headings @("Migration")) -and ((Get-Content -LiteralPath $note -Raw) -match "pressure-night|kPa|psi|bar")
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
  "official-facts" {
    $map = New-ObservationMap -Keys @("installation", "operation", "permissions", "cost", "date", "no_live_claim")
    $official = Join-Path $repo "worklog\official-sources.md"
    $text = if (Test-Path -LiteralPath $official -PathType Leaf) { Get-Content -LiteralPath $official -Raw } else { "" }
    $map.installation = $text -match "https://code\.claude\.com/docs/en/installation"
    $map.operation = $text -match "https://code\.claude\.com/docs/en/common-workflows"
    $map.permissions = $text -match "https://code\.claude\.com/docs/en/permissions"
    $map.cost = $text -match "https://code\.claude\.com/docs/en/costs"
    $map.date = $text -match "2026-08-13"
    $map.no_live_claim = $text -match "(?i)not.*verified|未验证|未完成 live"
    $map
  }
  "failure-observed" {
    $map = New-ObservationMap -Keys @("expected_failure", "error_classified", "no_fake_result")
    $test = Get-TestRun -Repo $repo
    $map.expected_failure = $test.ExitCode -ne 0
    $map.error_classified = [regex]::IsMatch([string]$test.Output, "(?i)fail|assert|error")
    $map.no_fake_result = (Get-Content -LiteralPath (Join-Path $repo "CLAUDE.md") -Raw) -match "(?i)not.*verified|不要伪造"
    $map
  }
  "change" {
    $map = New-ObservationMap -Keys @("source_changed", "diff", "approval", "variant_changed")
    $map.source_changed = $changedPaths -contains "src/pressure_report.py"
    $diff = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--quiet")
    $map.diff = $diff.ExitCode -eq 1
    $map.approval = [bool]$HumanApproved
    $source = Get-Content -LiteralPath (Join-Path $repo "src\pressure_report.py") -Raw
    $map.variant_changed = $source -match "pressure-report-v1" -and $source -match "mean_kpa" -and $source -match "alarm_count"
    $map
  }
  "recovery" {
    $map = New-ObservationMap -Keys @("tests_passed", "report_generated", "summary_only")
    $tests = Get-TestRun -Repo $repo
    $reportRun = Get-ReportRun -Repo $repo
    $map.tests_passed = $tests.ExitCode -eq 0
    $map.report_generated = $reportRun.ExitCode -eq 0 -and (Test-Report -Repo $repo)
    $reportPath = Join-Path $repo "artifacts\report.json"
    $reportText = if (Test-Path -LiteralPath $reportPath -PathType Leaf) { Get-Content -LiteralPath $reportPath -Raw } else { "" }
    $map.summary_only = $reportText -notmatch "timestamp|rows|not-a-timestamp"
    $map
  }
  "review" {
    $map = New-ObservationMap -Keys @("diff_reviewed", "scope_clean", "no_secrets", "path_complete")
    $diffCheck = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--check")
    $diffText = Invoke-Git -Repo $repo -Arguments @("diff", "HEAD", "--")
    $map.diff_reviewed = $diffCheck.ExitCode -eq 0
    $map.scope_clean = Test-AllowedScope -Paths $changedPaths
    $map.no_secrets = -not [regex]::IsMatch([string]$diffText.Output, "(?i)sk-[A-Za-z0-9]{10,}|password\s*=|token\s*=|BEGIN PRIVATE KEY")
    $map.path_complete = Test-PathNote -Repo $repo -Mode $PathMode
    $map
  }
  "delivery" {
    $map = New-ObservationMap -Keys @("handoff", "evidence_ready", "human_approved", "live_call_not_claimed")
    $map.handoff = Test-CompleteNote -Path (Join-Path $repo "worklog\handoff.md") -Headings @("Diff", "Verification", "Decision")
    $map.evidence_ready = (Test-Path -LiteralPath (Join-Path $repo "artifacts\report.json") -PathType Leaf) -and ($recordsBefore.Count -eq 8)
    $map.human_approved = [bool]$HumanApproved
    $map.live_call_not_claimed = (Get-Content -LiteralPath (Join-Path $repo "worklog\claude-only.md") -Raw) -match "(?i)not-verified|不调用|不包含"
    $map
  }
}

$result = Get-Result -Observations $observations
$record = [ordered]@{
  lesson_id = "t04-claude-migration"
  trace_version = "1"
  trace_id = $traceId
  mode = $PathMode
  stage = $Stage
  sequence = $stageIndex + 1
  result = $result
  observations = $observations
}
$recordPath = Join-Path $stageDirectory ("{0:D2}-{1}.json" -f ($stageIndex + 1), $Stage)
if ((Test-Path -LiteralPath $recordPath) -and -not $AllowOverwrite) { throw "Stage record already exists; pass -AllowOverwrite only after reviewing it." }
Write-JsonFile -Path $recordPath -Value (($record | ConvertTo-Json -Depth 8) + "`n")

if ($Stage -ne "delivery") {
  [ordered]@{ lesson_id = "t04-claude-migration"; stage = $Stage; result = $result; mode = $PathMode; live_call = "not-verified" } | ConvertTo-Json -Compress
  exit 0
}

$allRecords = @(Read-Records -Directory $stageDirectory)
if ($allRecords.Count -ne $stageOrder.Count) { throw "The delivery stage requires the complete ordered journey." }
$publicStages = @(
  foreach ($item in $allRecords) {
    [ordered]@{ id = [string]$item.stage; sequence = [int]$item.sequence; result = [string]$item.result; observations = $item.observations }
  }
)
$stagePassed = @{}
foreach ($item in $allRecords) { $stagePassed[[string]$item.stage] = [string]$item.result -eq "passed" }
$checks = @(
  [ordered]@{ id = "clarification-recorded"; result = if ($stagePassed["clarify"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "plan-recorded"; result = if ($stagePassed["plan"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "official-facts-recorded"; result = if ($stagePassed["official-facts"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "migration-input-changed"; result = if ($stagePassed["change"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "failure-recovered"; result = if ($stagePassed["failure-observed"] -and $stagePassed["recovery"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "tests-passed"; result = if ($stagePassed["recovery"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "permission-cost-compared"; result = if ($stagePassed["official-facts"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "path-completed"; result = if ($stagePassed["review"]) { "passed" } else { "failed" } }
  [ordered]@{ id = "live-claude-not-claimed"; result = if ($stagePassed["official-facts"] -and $stagePassed["delivery"]) { "passed" } else { "failed" } }
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
$experiment = [ordered]@{
  version = "1"
  mode = $PathMode
  migration_variant = "pressure-night"
  input_contract = [ordered]@{
    subject = "pressure"
    units = @("kPa", "psi", "bar")
    record_limit = "recent-3-valid"
    outputs = @("mean_kpa", "peak_kpa", "alarm_count")
  }
  official_facts = [ordered]@{ installation = "recorded"; operation = "recorded"; permissions = "recorded"; cost = "recorded" }
  live_call = "not-verified"
  codex_reference = if ($PathMode -eq "claude-only") { "not-required" } else { "status-only" }
}
$document = [ordered]@{
  contract = "agent-engineering-course/evidence"
  contract_version = "1"
  course_version = $CourseVersion
  lesson_id = "t04-claude-migration"
  result = $documentResult
  anonymous = $true
  checked_on = (Get-Date).ToString("yyyy-MM-dd")
  summary = $summary
  evidence = $checks
  task_id = "pressure-report-v1"
  platform = "windows"
  shell = "powershell"
  experiment = $experiment
  journey = [ordered]@{ trace_version = "1"; trace_id = $traceId; stages = $publicStages }
  artifact = [ordered]@{ version = "1"; report = if ($stagePassed["recovery"]) { "passed" } else { "failed" }; tests = if ($stagePassed["recovery"]) { "passed" } else { "failed" }; delivery = if ($stagePassed["delivery"]) { "passed" } else { "failed" } }
}
Write-JsonFile -Path $safeOutput -Value (($document | ConvertTo-Json -Depth 12) + "`n")
[ordered]@{ lesson_id = "t04-claude-migration"; result = $documentResult; output = "anonymous-evidence"; mode = $PathMode; live_call = "not-verified" } | ConvertTo-Json -Compress
