param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [ValidateSet('research', 'enterprise')]
    [string]$Track = 'enterprise',
    [ValidateSet('none', 'missing-core', 'unsafe-side-effect', 'incomplete-delivery')]
    [string]$Fault = 'none'
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runner = Join-Path $repoRoot 'labs\capstone-integration\run_lab.py'
& python $runner --output $OutputPath --track $Track --fault $Fault
if ($LASTEXITCODE -ne 0) {
    throw "capstone integration runner failed with exit code $LASTEXITCODE"
}
