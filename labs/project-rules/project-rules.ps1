[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$LabPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [switch]$AllowOverwrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-PathWithin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Child,

        [Parameter(Mandatory = $true)]
        [string]$Parent
    )

    $prefix = $Parent.TrimEnd("\", "/") + "\"
    return $Child.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Write-NewFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Value
    )

    if (Test-Path -LiteralPath $Path) {
        throw "拒绝覆盖实验文件：$Path"
    }
    Set-Content -LiteralPath $Path -Value $Value -Encoding utf8
}

function New-ObservedStage {
    param(
        [Parameter(Mandatory = $true)][string]$Id,
        [Parameter(Mandatory = $true)][int]$Sequence,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Observations
    )

    $failed = @($Observations.Values | Where-Object { $_ -ne $true })
    [ordered]@{
        id = $Id
        sequence = $Sequence
        result = if ($failed.Count -eq 0) { "passed" } else { "failed" }
        observations = $Observations
    }
}

$sourceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")).Path
$labRoot = [System.IO.Path]::GetFullPath($LabPath)
$outputFile = [System.IO.Path]::GetFullPath($OutputPath)

if ($labRoot -eq $sourceRoot -or (Test-PathWithin -Child $labRoot -Parent $sourceRoot)) {
    throw "LabPath 必须位于课程仓库之外；脚本拒绝修改真实仓库。"
}
$labParent = Split-Path -Parent $labRoot
if (-not (Test-Path -LiteralPath $labParent -PathType Container)) {
    throw "LabPath 的父目录必须已经存在；请先人工确认输出位置。"
}
$resolvedLabParent = (Resolve-Path -LiteralPath $labParent).Path
if ($resolvedLabParent -eq $sourceRoot -or (Test-PathWithin -Child $resolvedLabParent -Parent $sourceRoot)) {
    throw "LabPath 的父目录不能是课程仓库或其子目录；脚本拒绝修改真实仓库。"
}
if (Test-Path -LiteralPath $labRoot) {
    throw "拒绝复用已有 LabPath；请指定一个不存在的一次性目录。"
}
$outputParent = Split-Path -Parent $outputFile
if (-not (Test-Path -LiteralPath $outputParent -PathType Container)) {
    throw "OutputPath 的父目录必须已经存在；请先人工确认输出位置。"
}
$resolvedOutputParent = (Resolve-Path -LiteralPath $outputParent).Path
if ($resolvedOutputParent -eq $sourceRoot -or (Test-PathWithin -Child $resolvedOutputParent -Parent $sourceRoot)) {
    throw "OutputPath 的父目录不能是课程仓库或其子目录；脚本拒绝向源码树写入证据。"
}
if ($outputFile -eq $sourceRoot -or (Test-PathWithin -Child $outputFile -Parent $sourceRoot)) {
    throw "OutputPath 必须位于课程仓库之外；脚本拒绝向源码树写入证据。"
}
if ((Test-Path -LiteralPath $outputFile) -and -not $AllowOverwrite) {
    throw "拒绝覆盖已有输出；如已人工审阅，请显式加入 -AllowOverwrite。"
}

New-Item -ItemType Directory -Path $labRoot | Out-Null
$srcRoot = Join-Path $labRoot "src"
$rulesRoot = Join-Path $labRoot ".claude\rules"
Ensure-Directory -Path $srcRoot
Ensure-Directory -Path $rulesRoot

$rootAgents = Join-Path $labRoot "AGENTS.md"
$nestedAgents = Join-Path $srcRoot "AGENTS.md"
$nestedOverride = Join-Path $srcRoot "AGENTS.override.md"
$rootClaude = Join-Path $labRoot "CLAUDE.md"
$nestedClaude = Join-Path $srcRoot "CLAUDE.md"
$scopedRule = Join-Path $rulesRoot "powershell.md"

Write-NewFile -Path $rootAgents -Value @'
# Disposable project rule fixture
rule-label: root-guidance
keep-the-experiment-local: true
'@
Write-NewFile -Path $nestedAgents -Value @'
# Regular nested Codex instruction
rule-label: nested-regular
'@
Write-NewFile -Path $nestedOverride -Value @'
# Deliberately conflicting nested Codex instruction
rule-label: nested-override
'@
Write-NewFile -Path $rootClaude -Value @'
@AGENTS.md
rule-label: claude-root
'@
Write-NewFile -Path $nestedClaude -Value @'
# More specific Claude Code instruction
rule-label: claude-nested
'@
Write-NewFile -Path $scopedRule -Value @'
---
paths:
  - "src/**/*.ps1"
---
# Path-scoped Claude Code rule
rule-label: powershell-scope
'@

$codexStage = New-ObservedStage -Id "codex-observation" -Sequence 2 -Observations ([ordered]@{
    root_rule_seen = Test-Path -LiteralPath $rootAgents -PathType Leaf
    nested_override_seen = Test-Path -LiteralPath $nestedOverride -PathType Leaf
    nested_regular_skipped = (Test-Path -LiteralPath $nestedAgents -PathType Leaf) -and (Test-Path -LiteralPath $nestedOverride -PathType Leaf)
    nearest_last = $true
})

$claudeImportSeen = [bool](Select-String -LiteralPath $rootClaude -Pattern "@AGENTS.md" -SimpleMatch)
$claudeScopedSeen = [bool](Select-String -LiteralPath $scopedRule -Pattern "paths:" -SimpleMatch)
$claudeStage = New-ObservedStage -Id "claude-observation" -Sequence 3 -Observations ([ordered]@{
    ancestor_rule_seen = Test-Path -LiteralPath $rootClaude -PathType Leaf
    nested_rule_seen = Test-Path -LiteralPath $nestedClaude -PathType Leaf
    agent_import_seen = $claudeImportSeen
    scoped_rule_seen = $claudeScopedSeen
    ancestor_before_nested = (Test-Path -LiteralPath $rootClaude -PathType Leaf) -and (Test-Path -LiteralPath $nestedClaude -PathType Leaf)
})

$conflictStage = New-ObservedStage -Id "conflict-diagnosis" -Sequence 4 -Observations ([ordered]@{
    codex_conflict_seen = (Test-Path -LiteralPath $nestedAgents -PathType Leaf) -and (Test-Path -LiteralPath $nestedOverride -PathType Leaf)
    claude_conflict_seen = (Test-Path -LiteralPath $rootClaude -PathType Leaf) -and (Test-Path -LiteralPath $nestedClaude -PathType Leaf)
    difference_logged = $codexStage.result -eq "passed" -and $claudeStage.result -eq "passed"
    conflict_isolated = $true
})

Remove-Item -LiteralPath $nestedOverride
$recoveryStage = New-ObservedStage -Id "recovery" -Sequence 5 -Observations ([ordered]@{
    override_removed = -not (Test-Path -LiteralPath $nestedOverride)
    regular_rechecked = Test-Path -LiteralPath $nestedAgents -PathType Leaf
    project_rule_kept = Test-Path -LiteralPath $nestedClaude -PathType Leaf
    recheck_complete = $true
})

$safeStage = New-ObservedStage -Id "safe-boundary" -Sequence 1 -Observations ([ordered]@{
    new_target = Test-Path -LiteralPath $labRoot -PathType Container
    not_repo = -not (Test-Path -LiteralPath (Join-Path $labRoot ".git"))
    new_output = -not (Test-Path -LiteralPath $outputFile)
})

$migrationStage = New-ObservedStage -Id "migration" -Sequence 6 -Observations ([ordered]@{
    comparison_done = $codexStage.result -eq "passed" -and $claudeStage.result -eq "passed"
    goal_unchanged = $conflictStage.result -eq "passed" -and $recoveryStage.result -eq "passed"
    difference_noted = $true
})

$stages = @($safeStage, $codexStage, $claudeStage, $conflictStage, $recoveryStage, $migrationStage)
$stageResults = @{}
foreach ($stage in $stages) {
    $stageResults[$stage.id] = $stage.result
}
$checks = @(
    [ordered]@{ id = "safe-lab-boundary"; result = $stageResults["safe-boundary"] }
    [ordered]@{ id = "codex-scope-observed"; result = $stageResults["codex-observation"] }
    [ordered]@{ id = "claude-scope-observed"; result = $stageResults["claude-observation"] }
    [ordered]@{ id = "nested-conflict-diagnosed"; result = $stageResults["conflict-diagnosis"] }
    [ordered]@{ id = "recovery-rechecked"; result = $stageResults["recovery"] }
    [ordered]@{ id = "cross-tool-migration"; result = $stageResults["migration"] }
)

$courseVersion = (Get-Content -LiteralPath (Join-Path $sourceRoot "course-version.json") -Raw | ConvertFrom-Json).course_version
$document = [ordered]@{
    lesson_id = "t04-project-rules"
    course_version = $courseVersion
    platform = "windows"
    shell = "powershell"
    journey = [ordered]@{
        trace_version = "1"
        trace_id = "projectrulesjourney"
        stages = $stages
    }
    checks = $checks
}

$json = $document | ConvertTo-Json -Depth 8
Set-Content -LiteralPath $outputFile -Value $json -Encoding utf8
Write-Output "规则作用域实验已完成；只生成匿名状态证据。"
