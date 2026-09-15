param(
    [ValidateSet('Install','Start','Stop','Status','Uninstall')]
    [string]$Action = 'Status',
    [ValidateSet('male','female')]
    [string]$Sex = 'male',
    [double]$Hours = 24,
    [double]$DelaySeconds = 5
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$statusPath = Join-Path $projectRoot 'web/data/internet_status.json'
$dashboardTask = 'NerdyFlyDashboard'
$explorerTask = 'NerdyFlyExplorer'
$reasonerTask = 'NerdyFlyReasoner'
$pythonPath = (Get-Command python).Source
$stateDir = Join-Path $projectRoot 'work'
$explorerStop = Join-Path $stateDir 'explorer.stop'
$reasonerStop = Join-Path $stateDir 'reasoner.stop'

function Get-FlyTask([string]$Name) {
    Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
}

function Install-FlyTasks {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Days 2) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
    $dashboardAction = New-ScheduledTaskAction -Execute $pythonPath -Argument 'server.py' -WorkingDirectory $projectRoot
    $explorerArgs = "tools/internet_explorer.py --sex $Sex --hours $Hours --steps 100000 --delay $DelaySeconds --seed 23 --checkpoint-every 5"
    $explorerAction = New-ScheduledTaskAction -Execute $pythonPath -Argument $explorerArgs -WorkingDirectory $projectRoot
    $reasonerAction = New-ScheduledTaskAction -Execute $pythonPath -Argument "tools/reasoning_agent.py --model qwen3.5:2b --sex $Sex --hours $Hours --interval 60" -WorkingDirectory $projectRoot
    Register-ScheduledTask -TaskName $dashboardTask -Action $dashboardAction -Trigger $trigger -Principal $principal -Settings $settings -Description 'Loopback-only Nerdy Fly dashboard' -Force | Out-Null
    Register-ScheduledTask -TaskName $explorerTask -Action $explorerAction -Trigger $trigger -Principal $principal -Settings $settings -Description 'Checkpointed connectome-informed web explorer' -Force | Out-Null
    Register-ScheduledTask -TaskName $reasonerTask -Action $reasonerAction -Trigger $trigger -Principal $principal -Settings $settings -Description 'Local Qwen reasoning and language layer with connectome context' -Force | Out-Null
    Write-Output "Installed independent Windows tasks for $identity."
}

function Stop-FlyTasks {
    New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
    Set-Content -LiteralPath $explorerStop -Value (Get-Date).ToString('o')
    Set-Content -LiteralPath $reasonerStop -Value (Get-Date).ToString('o')
    for ($attempt=0; $attempt -lt 55; $attempt++) {
        $active = @($explorerTask,$reasonerTask) | Where-Object { $task=Get-FlyTask $_; $task -and $task.State -eq 'Running' }
        if (-not $active) { break }
        Start-Sleep -Seconds 1
    }
    foreach ($name in @($reasonerTask,$explorerTask,$dashboardTask)) {
        $task = Get-FlyTask $name
        if ($task -and $task.State -eq 'Running') { Stop-ScheduledTask -TaskName $name }
    }
}

switch ($Action) {
    'Install' {
        & $pythonPath (Join-Path $projectRoot 'tools/snapshot_state.py')
        Stop-FlyTasks
        Install-FlyTasks
    }
    'Start' {
        if (-not (Get-FlyTask $dashboardTask) -or -not (Get-FlyTask $explorerTask) -or -not (Get-FlyTask $reasonerTask)) { Install-FlyTasks }
        foreach ($path in @($explorerStop,$reasonerStop)) { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path } }
        if ((Get-FlyTask $dashboardTask).State -ne 'Running') { Start-ScheduledTask -TaskName $dashboardTask }
        if ((Get-FlyTask $explorerTask).State -ne 'Running') { Start-ScheduledTask -TaskName $explorerTask }
        if ((Get-FlyTask $reasonerTask).State -ne 'Running') { Start-ScheduledTask -TaskName $reasonerTask }
        Start-Sleep -Seconds 2
        Write-Output 'Started independently of Codex. Dashboard: http://127.0.0.1:8787'
    }
    'Stop' {
        Stop-FlyTasks
        & $pythonPath (Join-Path $projectRoot 'tools/snapshot_state.py')
        Write-Output 'Stopped scheduled tasks. Atomic checkpoints and corpus remain recoverable.'
    }
    'Status' {
        foreach ($name in @($dashboardTask,$explorerTask,$reasonerTask)) {
            $task = Get-FlyTask $name
            if (-not $task) { Write-Output "$name NOT INSTALLED"; continue }
            $info = Get-ScheduledTaskInfo -TaskName $name
            Write-Output "$name $($task.State) last-result=$($info.LastTaskResult)"
        }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8787/' -TimeoutSec 3
            Write-Output "DASHBOARD HTTP $($response.StatusCode) http://127.0.0.1:8787"
        } catch { Write-Output 'DASHBOARD UNREACHABLE' }
        if (Test-Path -LiteralPath $statusPath) { Get-Content -Raw -LiteralPath $statusPath }
    }
    'Uninstall' {
        foreach ($name in @($reasonerTask,$explorerTask,$dashboardTask)) {
            $task = Get-FlyTask $name
            if ($task) {
                if ($task.State -eq 'Running') { Stop-ScheduledTask -TaskName $name }
                Unregister-ScheduledTask -TaskName $name -Confirm:$false
            }
        }
        Write-Output 'Removed Nerdy Fly scheduled tasks. Data and checkpoints were not deleted.'
    }
}
