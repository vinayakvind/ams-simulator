param(
    [Parameter(Mandatory = $true)][string]$PromptFile,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [int]$MaxAutopilotContinues = 25,
    [string]$CopilotPath = "",
    [switch]$UseCliContinue
)

if (-not $CopilotPath) {
    $CopilotPath = Join-Path $env:APPDATA "Code\User\globalStorage\github.copilot-chat\copilotCli\copilot.ps1"
}

if (-not (Test-Path $PromptFile)) {
    Write-Error "Prompt file not found: $PromptFile"
    exit 2
}

if (-not (Test-Path $CopilotPath)) {
    Write-Error "Copilot CLI bootstrapper not found: $CopilotPath"
    exit 3
}

$agentPrompt = Get-Content -Raw $PromptFile
$copilotArgs = @(
    "-p", $agentPrompt,
    "--allow-all",
    "--no-ask-user",
    "--autopilot",
    "--max-autopilot-continues", $MaxAutopilotContinues,
    "--add-dir", $RepoRoot
)

if ($UseCliContinue.IsPresent) {
    $copilotArgs += "--continue"
}

Push-Location $RepoRoot
try {
    & $CopilotPath @copilotArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}