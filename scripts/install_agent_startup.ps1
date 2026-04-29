param(
    [string]$TaskName = "AMS-Agent-CLI-Controller",
    [string]$StartupScript = (Join-Path $PSScriptRoot "open_agent_cli_window.ps1"),
    [int]$WatchIntervalSeconds = 86400,
    [int]$AgentLoopDelaySeconds = 60,
    [switch]$AtStartup,
    [switch]$AtLogon
)

$ErrorActionPreference = "Stop"

if (-not $AtStartup.IsPresent -and -not $AtLogon.IsPresent) {
    $AtLogon = $true
}

$scriptPath = (Resolve-Path $StartupScript).Path
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -WatchIntervalSeconds $WatchIntervalSeconds -AgentLoopDelaySeconds $AgentLoopDelaySeconds -ContinueOnAgentExit"
$launchDir = Join-Path $env:LOCALAPPDATA "AMSAgent"
$launchWrapper = Join-Path $launchDir "start_ams_agent_cli.cmd"

if (-not (Test-Path $launchDir)) {
    New-Item -Path $launchDir -ItemType Directory | Out-Null
}

$wrapperContent = @(
    "@echo off",
    "powershell.exe $arguments"
) -join "`r`n"
Set-Content -Path $launchWrapper -Value $wrapperContent -Encoding ASCII

$triggers = @()
if ($AtLogon.IsPresent) {
    $triggers += New-ScheduledTaskTrigger -AtLogOn
}
if ($AtStartup.IsPresent) {
    $triggers += New-ScheduledTaskTrigger -AtStartup
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$principal = New-ScheduledTaskPrincipal -UserId "$env:UserDomain\$env:UserName" -RunLevel Limited

function Register-WithSchtasks {
    param(
        [string]$Name,
        [string]$ActionCommand,
        [switch]$Startup,
        [switch]$Logon
    )

    if ($Startup.IsPresent -and $Logon.IsPresent) {
        throw "schtasks.exe fallback only supports one trigger per task. Retry with either -AtStartup or -AtLogon."
    }

    $schedule = if ($Startup.IsPresent) { "ONSTART" } else { "ONLOGON" }
    $argumentLine = "/Create /TN `"$Name`" /TR `"$ActionCommand`" /SC $schedule /RL LIMITED /F"
    $process = Start-Process -FilePath "schtasks.exe" -ArgumentList $argumentLine -NoNewWindow -Wait -PassThru
    if ($process.ExitCode -ne 0) {
        throw "schtasks.exe failed with exit code $($process.ExitCode)"
    }
}

function Install-StartupFolderLauncher {
    param(
        [string]$Name,
        [string]$WrapperPath
    )

    $startupFolder = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    $startupLauncher = Join-Path $startupFolder ("{0}.cmd" -f $Name)
    $startupContent = @(
        "@echo off",
        "call `"$WrapperPath`""
    ) -join "`r`n"

    Set-Content -Path $startupLauncher -Value $startupContent -Encoding ASCII
    return $startupLauncher
}

$registeredWith = $null
$startupLauncher = $null
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Force | Out-Null
    $registeredWith = "Register-ScheduledTask"
} catch {
    Write-Warning "Register-ScheduledTask failed: $($_.Exception.Message)"
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Principal $principal -Force | Out-Null
        $registeredWith = "Register-ScheduledTask -Principal"
    } catch {
        Write-Warning "Register-ScheduledTask with explicit principal failed: $($_.Exception.Message)"
        try {
            Register-WithSchtasks -Name $TaskName -ActionCommand $launchWrapper -Startup:$AtStartup.IsPresent -Logon:$AtLogon.IsPresent
            $registeredWith = "schtasks.exe"
        } catch {
            Write-Warning "schtasks.exe fallback failed: $($_.Exception.Message)"
            if ($AtStartup.IsPresent -and -not $AtLogon.IsPresent) {
                throw "Automatic startup registration requires scheduled-task permissions for -AtStartup. Retry with -AtLogon or run the installer elevated."
            }

            $startupLauncher = Install-StartupFolderLauncher -Name $TaskName -WrapperPath $launchWrapper
            $registeredWith = "Startup folder"
        }
    }
}

Write-Host "Startup registration installed via ${registeredWith}: $TaskName"
Write-Host "Startup launcher script: $scriptPath"
Write-Host "Launch wrapper: $launchWrapper"
if ($startupLauncher) {
    Write-Host "Startup launcher: $startupLauncher"
}
Write-Host "To override the default Copilot CLI bridge, set AMS_AGENT_COMMAND_TEMPLATE before the task runs."