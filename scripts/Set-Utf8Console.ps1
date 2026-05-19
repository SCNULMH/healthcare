$global:OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
chcp 65001 | Out-Null
Write-Host "PowerShell console encoding is now UTF-8."
