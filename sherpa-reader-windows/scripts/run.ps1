$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path ".\.venv\Scripts\python.exe")) { throw "请先运行 scripts\setup.ps1" }
& .\.venv\Scripts\python.exe .\app\main.py
