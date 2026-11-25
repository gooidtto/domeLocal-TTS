from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

import sherpa_onnx
import soundfile as sf
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QPushButton, QComboBox, QTextEdit, QVBoxLayout, QWidget
)

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "kokoro-multi-lang-v1_1"


def split_sentences(text: str) -> list[str]:
    """Preserve sentence order; sentence is the initial highlight unit."""
    chunks = re.split(r"(?<=[。！？!?；;.!])\s*|[\r\n]+", text)
    return [part.strip() for part in chunks if part.strip()]


def create_tts():
    required = ["model.onnx", "voices.bin", "tokens.txt",
                "lexicon-us-en.txt", "lexicon-zh.txt"]
    missing = [name for name in required if not (MODEL_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            "Kokoro 模型文件不完整：" + ", ".join(missing) +
            "。请先运行 scripts\\setup.ps1"
        )
    model = sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=str(MODEL_DIR / "model.onnx"),
            voices=str(MODEL_DIR / "voices.bin"),
            tokens=str(MODEL_DIR / "tokens.txt"),
            lexicon=",".join([
                str(MODEL_DIR / "lexicon-us-en.txt"),
                str(MODEL_DIR / "lexicon-zh.txt"),
            ]),
        ),
        num_threads=2,
        provider="cpu",
    )
    config = sherpa_onnx.OfflineTtsConfig(model=model)
    if not config.validate():
        raise RuntimeError("sherpa-onnx TTS 配置校验失败")
    return sherpa_onnx.OfflineTts(config)


class SynthesisWorker(QThread):
    ready = Signal(str, int, str)
    failed = Signal(str)

    def __init__(self, sentence: str, speaker_id: int, output_path: Path):
        super().__init__()
        self.sentence = sentence
        self.speaker_id = speaker_id
        self.output_path = output_path

    def run(self):
        try:
            tts = create_tts()
            generation = sherpa_onnx.GenerationConfig()
            generation.sid = self.speaker_id
            generation.speed = 1.0
            audio = tts.generate(self.sentence, generation)
            if len(audio.samples) == 0:
                raise RuntimeError("模型没有生成音频数据")
            sf.write(str(self.output_path), audio.samples, audio.sample_rate,
                     subtype="PCM_16")
            self.ready.emit(str(self.output_path), audio.sample_rate, self.sentence)
        except Exception as exc:
            self.failed.emit(str(exc))


class SherpaReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sherpa Reader for Windows")
        self.resize(1080, 760)
        self.sentences: list[str] = []
        self.index = 0
        self.worker = None
        self.temp_dir = Path(tempfile.mkdtemp(prefix="sherpa-reader-"))
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self.on_media_status)

        central = QWidget()
        layout = QVBoxLayout(central)
        bar = QHBoxLayout()

        open_button = QPushButton("打开 TXT / DOCX")
        open_button.clicked.connect(self.open_document)
        self.speaker = QComboBox()
        # v1.1 voice IDs are exposed as a selectable range; verify actual
        # language/voice mapping during the dedicated listening-test phase.
        for sid in range(103):
            self.speaker.addItem(f"Speaker {sid}", sid)
        self.speaker.setCurrentIndex(45)

        self.play_button = QPushButton("开始朗读")
        self.play_button.clicked.connect(self.start_reading)
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_reading)
        bar.addWidget(open_button)
        bar.addWidget(QLabel("声音 ID"))
        bar.addWidget(self.speaker)
        bar.addStretch(1)
        bar.addWidget(self.play_button)
        bar.addWidget(self.pause_button)
        bar.addWidget(self.stop_button)
        layout.addLayout(bar)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("打开 TXT / DOCX，或直接输入文本。")
        layout.addWidget(self.editor, 1)
        self.status = QLabel("就绪")
        layout.addWidget(self.status)
        self.setCentralWidget(central)

    def open_document(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "打开文档", "", "文档 (*.txt *.docx);;所有文件 (*.*)"
        )
        if not filename:
            return
        path = Path(filename)
        try:
            if path.suffix.lower() == ".docx":
                from docx import Document
                doc = Document(str(path))
                content = "\n".join(p.text for p in doc.paragraphs)
            else:
                raw = path.read_bytes()
                content = None
                for encoding in ("utf-8-sig", "utf-16", "gb18030"):
                    try:
                        content = raw.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        pass
                if content is None:
                    content = raw.decode("utf-8", errors="replace")
            self.editor.setPlainText(content)
            self.status.setText(f"已打开：{path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "打开失败", str(exc))

    def start_reading(self):
        content = self.editor.toPlainText().strip()
        if not content:
            QMessageBox.information(self, "提示", "请先打开文档或输入文本。")
            return
        self.sentences = split_sentences(content)
        self.index = 0
        self.play_button.setEnabled(False)
        self.synthesize_current()

    def synthesize_current(self):
        if self.index >= len(self.sentences):
            self.play_button.setEnabled(True)
            self.status.setText("朗读完成")
            return
        sentence = self.sentences[self.index]
        output = self.temp_dir / f"sentence-{self.index:06d}.wav"
        self.status.setText(f"正在合成第 {self.index + 1}/{len(self.sentences)} 句")
        self.worker = SynthesisWorker(sentence, int(self.speaker.currentData()), output)
        self.worker.ready.connect(self.on_audio_ready)
        self.worker.failed.connect(self.on_synthesis_failed)
        self.worker.start()

    def on_audio_ready(self, filename: str, _sample_rate: int, sentence: str):
        cursor = self.editor.document().find(sentence)
        if not cursor.isNull():
            self.editor.setTextCursor(cursor)
            self.editor.ensureCursorVisible()
        self.player.setSource(QUrl.fromLocalFile(filename))
        self.player.play()
        self.status.setText(f"正在朗读第 {self.index + 1}/{len(self.sentences)} 句")

    def on_synthesis_failed(self, message: str):
        self.play_button.setEnabled(True)
        self.status.setText("合成失败")
        QMessageBox.critical(self, "TTS 合成失败", message)

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.index += 1
            self.synthesize_current()

    def toggle_pause(self):
        state = self.player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.pause_button.setText("继续")
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            self.pause_button.setText("暂停")

    def stop_reading(self):
        self.player.stop()
        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait(1500)
        self.index = len(self.sentences)
        self.play_button.setEnabled(True)
        self.pause_button.setText("暂停")
        self.status.setText("已停止")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SherpaReader()
    window.show()
    sys.exit(app.exec())
