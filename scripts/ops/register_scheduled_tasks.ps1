# Register (or re-register) the two NSE-session-gated Windows scheduled tasks.
#   \Nifty\Orchestrator  daily 09:10  -> run_if_session.py orchestrator
#   \Nifty\DownloadAll   daily 20:00  -> run_if_session.py download
# Idempotent: existing tasks of the same name are replaced.
# Interactive logon is required: the orchestrator needs a console (Ctrl+C) and a
# browser for the Upstox login. No time limit on the orchestrator — a Task
# Scheduler kill would orphan its children and DuckDB writers.

$ErrorActionPreference = 'Stop'
$Root   = 'F:\Nifty'
$Python = 'C:\Program Files\Python313\python.exe'
$Gate   = "$Root\scripts\ops\run_if_session.py"
$Folder = '\Nifty\'
$User   = "$env:USERDOMAIN\$env:USERNAME"

$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

function Register-NiftyTask($Name, $At, $Target, $TimeLimit) {
    $action   = New-ScheduledTaskAction -Execute $Python -Argument "`"$Gate`" $Target" -WorkingDirectory $Root
    $trigger  = New-ScheduledTaskTrigger -Daily -At $At
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit $TimeLimit
    Unregister-ScheduledTask -TaskName $Name -TaskPath $Folder -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $Name -TaskPath $Folder -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal `
        -Description "Runs $Target only on NSE trading sessions (scripts/ops/run_if_session.py)" | Out-Null
    Write-Output "registered $Folder$Name at $At"
}

Register-NiftyTask 'Orchestrator' '09:10' 'orchestrator' ([TimeSpan]::Zero)
Register-NiftyTask 'DownloadAll'  '20:00' 'download'     (New-TimeSpan -Hours 4)
