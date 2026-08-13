param(
  [string]$OutputDirectory = (Join-Path $env:TEMP "agent-engineering-course\t19-mcp-discovery"),
  [switch]$AllowOverwrite
)

$ErrorActionPreference = "Stop"
$labRoot = (Resolve-Path -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $labRoot "..\..")).Path
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)

if ([string]::IsNullOrWhiteSpace($outputRoot) -or $outputRoot -eq [System.IO.Path]::GetPathRoot($outputRoot)) {
  throw "OutputDirectory must be a specific, non-root directory."
}
if ($outputRoot -eq $workspaceRoot -or $outputRoot.StartsWith("$workspaceRoot\", [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Refusing to write lesson evidence inside the course workspace; choose a temporary directory."
}
if ((Test-Path -LiteralPath $outputRoot) -and -not $AllowOverwrite) {
  throw "OutputDirectory already exists. Review it or choose a new path; use -AllowOverwrite only after review."
}
if (-not (Test-Path -LiteralPath $outputRoot)) {
  New-Item -ItemType Directory -Path $outputRoot | Out-Null
}

$venvCandidates = @(
  (Join-Path $labRoot ".venv\Scripts\python.exe"),
  (Join-Path $workspaceRoot ".venv\Scripts\python.exe")
)
$venvPython = $venvCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -ne $venvPython) {
  $python = $venvPython
} elseif ($null -ne $pythonCommand) {
  $python = $pythonCommand.Source
} else {
  throw "Python 3.11+ was not found. Create a venv and install requirements.lock first."
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCommand) {
  throw "Node.js is required for the official Inspector CLI."
}

$inspectorOutput = Join-Path $outputRoot "inspector.json"
$clientOutput = Join-Path $outputRoot "mcp-client.json"
$checkedOutput = Join-Path $outputRoot "t19-mcp-discovery-evidence.json"

& $nodeCommand.Source (Join-Path $labRoot "inspector-check.mjs") --python $python --output $inspectorOutput
if ($LASTEXITCODE -ne 0) { throw "Inspector capability check failed." }

& $python (Join-Path $labRoot "mcp_client.py") --inspector-evidence $inspectorOutput --output $clientOutput
if ($LASTEXITCODE -ne 0) { throw "Python MCP client failed." }

$checkerRoot = Join-Path $workspaceRoot "checker"
Push-Location -LiteralPath $checkerRoot
try {
  & $python -m course_check check t19-mcp-discovery --root $workspaceRoot --evidence-file $clientOutput --output $checkedOutput --json
  if ($LASTEXITCODE -ne 0) { throw "course_check did not accept the MCP evidence." }
} finally {
  Pop-Location
}

Write-Output "Formal MCP evidence written to $checkedOutput"
