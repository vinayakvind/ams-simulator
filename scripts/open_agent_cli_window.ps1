param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [int]$WatchIntervalSeconds = 86400,
    [int]$AgentLoopDelaySeconds = 60,
    [string]$QueueFile = "scripts/agent_workflow.json",
    [string]$WindowTitle = "AMS Agent CLI Daemon",
    [string]$AgentCommandTemplate = $env:AMS_AGENT_COMMAND_TEMPLATE,
    [switch]$ContinueOnAgentExit
)

$repoPath = (Resolve-Path $RepoRoot).Path
$queuePath = if ([System.IO.Path]::IsPathRooted($QueueFile)) {
    $QueueFile
} else {
    (Join-Path $repoPath $QueueFile)
}
$daemonScript = (Resolve-Path (Join-Path $PSScriptRoot "start_agent_cli_daemon.ps1")).Path

function ConvertTo-SingleQuotedLiteral {
    param([string]$Value)
    return $Value.Replace("'", "''")
}

$safeWindowTitle = ConvertTo-SingleQuotedLiteral $WindowTitle
$safeRepoPath = ConvertTo-SingleQuotedLiteral $repoPath
$safeQueuePath = ConvertTo-SingleQuotedLiteral $queuePath
$safeDaemonScript = ConvertTo-SingleQuotedLiteral $daemonScript

$daemonInvocation = "& '$safeDaemonScript' -RepoRoot '$safeRepoPath' -QueueFile '$safeQueuePath' -WatchIntervalSeconds $WatchIntervalSeconds -AgentLoopDelaySeconds $AgentLoopDelaySeconds"
if ($ContinueOnAgentExit.IsPresent) {
    $daemonInvocation += " -ContinueOnAgentExit"
}

$commands = @(
    '& {',
    "$host.UI.RawUI.WindowTitle = '$safeWindowTitle';",
    "Set-Location '$safeRepoPath';"
)

if ($AgentCommandTemplate) {
    $safeTemplate = ConvertTo-SingleQuotedLiteral $AgentCommandTemplate
    $commands += "$env:AMS_AGENT_COMMAND_TEMPLATE = '$safeTemplate';"
}

$commands += $daemonInvocation
$commands += '}'

$process = Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-Command", ($commands -join ' ')
) -WorkingDirectory $repoPath -PassThru

Write-Host "Opened visible agent window PID=$($process.Id)"
Write-Host "Repo root: $repoPath"
Write-Host "Queue file: $queuePath"
