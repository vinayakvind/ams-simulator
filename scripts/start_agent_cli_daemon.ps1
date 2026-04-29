param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [int]$WatchIntervalSeconds = 86400,
    [int]$AgentLoopDelaySeconds = 60,
    [string]$QueueFile = "scripts/agent_workflow.json",
    [string]$AgentCommandTemplate = $env:AMS_AGENT_COMMAND_TEMPLATE,
    [switch]$ContinueOnAgentExit
)

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

$controller = Join-Path $RepoRoot "scripts\agent_cli_controller.py"
$copilotRunner = Join-Path $RepoRoot "scripts\run_copilot_prompt.ps1"

if (-not $AgentCommandTemplate -and (Test-Path $copilotRunner)) {
    $AgentCommandTemplate = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$copilotRunner`" -PromptFile `"{prompt_file}`" -RepoRoot `"{repo_root}`""
}

$arguments = @(
    $controller,
    "--repo", $RepoRoot,
    "--queue-file", $QueueFile,
    "--watch",
    "--watch-interval-seconds", $WatchIntervalSeconds,
    "--agent-loop-delay-seconds", $AgentLoopDelaySeconds
)

if ($ContinueOnAgentExit.IsPresent) {
    $arguments += "--continue-on-agent-exit"
}

if ($AgentCommandTemplate) {
    $env:AMS_AGENT_COMMAND_TEMPLATE = $AgentCommandTemplate
}

Push-Location $RepoRoot
try {
    & $python @arguments
} finally {
    Pop-Location
}