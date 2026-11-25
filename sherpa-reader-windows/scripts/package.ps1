$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw '请先运行 scripts\setup.ps1' }
& $Python -m PyInstaller --noconfirm --clean --windowed --name SherpaReader --collect-all sherpa_onnx --collect-all soundfile app\main.py
Write-Host 'EXE 构建完成：dist\SherpaReader\SherpaReader.exe'
Write-Host 'Kokoro 模型目录需放在 EXE 旁边的 models\kokoro-multi-lang-v1_1。'
