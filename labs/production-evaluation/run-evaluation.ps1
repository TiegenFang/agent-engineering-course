[CmdletBinding()]
param(
  [Parameter()]
  [string] $OutputPath = (Join-Path ([System.IO.Path]::GetTempPath()) 't29-production-evaluation.json'),
  [Parameter()]
  [double] $BudgetUsd = 0.01
)

$scriptPath = Join-Path $PSScriptRoot 'evaluate.py'
$fixturePath = Join-Path $PSScriptRoot 'fixtures\baseline.json'
$pythonArgs = @(
  $scriptPath,
  '--fixture', $fixturePath,
  '--budget-usd', $BudgetUsd.ToString([System.Globalization.CultureInfo]::InvariantCulture),
  '--output', $OutputPath
)
& python @pythonArgs
if ($LASTEXITCODE -ne 0) {
  throw "T29 evaluator failed with exit code $LASTEXITCODE"
}
Write-Output "Wrote anonymous T29 evaluation evidence to $OutputPath"
