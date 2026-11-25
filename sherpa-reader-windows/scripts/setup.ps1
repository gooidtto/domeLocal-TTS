$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher 未找到。请安装 Python 3.11 x64，并启用 py 命令。"
}

py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

$modelDir = Join-Path $Root "models\kokoro-multi-lang-v1_1"
$archive = Join-Path $Root "models\kokoro-multi-lang-v1_1.tar.bz2"
New-Item -ItemType Directory -Force -Path (Split-Path $modelDir) | Out-Null

if (-not (Test-Path (Join-Path $modelDir "model.onnx"))) {
    $url = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2"
    Invoke-WebRequest -Uri $url -OutFile $archive
    tar -xjf $archive -C (Split-Path $modelDir)
    Remove-Item $archive -Force
}

if (-not (Test-Path (Join-Path $modelDir "model.onnx"))) {
    throw "模型解压失败：未找到 model.onnx。请核对官方 Release 包结构。"
}
Write-Host "依赖和 Kokoro Multilingual 模型准备完成。"
