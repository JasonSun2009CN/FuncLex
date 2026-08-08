"""发音功能 - 封装 QTextToSpeech（系统离线 TTS 引擎，无需网络/音频文件）"""
from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtTextToSpeech import QTextToSpeech


class PronounceHelper(QObject):
    """封装 QTextToSpeech 的轻量助手。

    说明：项目内 Collins Cobuild Audio.mdx 只有 sound:// 引用、无配套 .mdd，
    真实音频无法播放；发音统一走系统 TTS（macOS 原生、Windows SAPI、Linux speechd）。
    若日后补充 .mdd，可在此切换到 QtMultimedia 播放真实原声。
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tts: QTextToSpeech | None = None
        try:
            self._tts = QTextToSpeech(self)
        except Exception as e:
            print(f"[PronounceHelper] QTextToSpeech init failed: {e}")

    @property
    def available(self) -> bool:
        return self._tts is not None

    def speak(self, text: str) -> None:
        """朗读给定文本（非阻塞，异步）。"""
        if not text or self._tts is None:
            return
        self.stop()
        self._tts.say(text.strip())

    def stop(self) -> None:
        if self._tts is not None:
            try:
                self._tts.stop()
            except Exception:
                pass
