# Sherpa Reader for Windows

独立 Windows 桌面阅读器开发目录。当前开发分支：`feature/sherpa-reader-windows`。

## 当前技术路线

- UI：PySide6
- TTS：sherpa-onnx Python API（Windows CPU wheel）
- 首选模型：Kokoro Multilingual v1.1
- 文档：TXT / DOCX；旧版 DOC 后续通过 LibreOffice 转换适配
- 播放：QMediaPlayer
- 长文：按句切分、逐句合成和播放
- 跟随：第一阶段逐句高亮；不伪造逐字对齐时间戳

## Windows 10/11 x64 开发

需要 Python 3.10–3.12（建议 3.11）：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\run.ps1
```

脚本会创建 .venv、安装依赖并下载 Kokoro Multilingual v1.1 模型。

## 打包 Windows EXE

```powershell
.\.venv\Scripts\Activate.ps1
pyinstaller --noconfirm --clean --windowed --name SherpaReader app\main.py
```

模型默认保存在项目的 `models\kokoro-multi-lang-v1_1`，不嵌入 EXE。首次准备模型需要联网；模型下载完成后可离线运行。

## 模型文件

下载源：sherpa-onnx 官方 GitHub Release：
`https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_1.tar.bz2`

必须检查解压目录包含：
- `model.onnx`
- `voices.bin`
- `tokens.txt`
- `lexicon-us-en.txt`
- `lexicon-zh.txt`

## 迭代阶段

1. 模型加载、中文/英文/混合文本合成与声音试听
2. TXT/DOCX 阅读、连续播放、暂停/继续/停止
3. 逐句高亮与自动滚动
4. DOC 支持、声音试听列表、设置持久化
5. Windows 安装包、依赖收集和离线部署验证

## 许可证

Sherpa Reader 自身代码与 sherpa-onnx、Kokoro 模型及第三方依赖分别遵循各自许可证。发布前需要逐项核验。


## CI

GitHub Actions workflow: `.github/workflows/sherpa-reader-windows.yml`. It runs Windows x64 dependency installation, Python compilation, sentence-splitting tests, PyInstaller packaging, and uploads a build artifact.


当前句子跟随使用单调向前的文档游标，避免相同句子重复出现时跳回前文。
