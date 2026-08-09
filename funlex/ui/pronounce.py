"""发音助手 - 真实音频（.mdd）优先，TTS 合成回退；来源明确标注

- 若提供了 .mdd 音频索引（如 oald10.mdd），优先播放真实牛津原声（英/美音）
- 否则回退系统 TTS 合成；last_source 区分 'real' / 'tts'，UI 据此标注
- 播放用临时文件 + QtMultimedia（QMediaPlayer），短音频安全可靠
"""
from __future__ import annotations

import os
import tempfile

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtTextToSpeech import QTextToSpeech

from funlex.core.audio import MddAudioIndex


class PronounceHelper(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._tts: QTextToSpeech | None = None
        self._audio_index: MddAudioIndex | None = None
        self._player: QMediaPlayer | None = None
        self._audio_output: QAudioOutput | None = None
        self._voices: dict = {}
        self._last_tmp: str | None = None
        # 最近一次发音来源：'real'（牛津原声）/ 'tts'（合成）
        self.last_source = "tts"

        try:
            self._tts = QTextToSpeech(self)
            self._pick_voices()
        except Exception as e:
            print(f"[PronounceHelper] init failed: {e}")
            self._tts = None

    @property
    def available(self) -> bool:
        return self._tts is not None or self.has_real_audio_index

    @property
    def has_real_audio_index(self) -> bool:
        return self._audio_index is not None and self._audio_index.loaded

    def has_audio(self, word: str, variant: str = "") -> bool:
        """真实音频索引里是否含该词原声"""
        if self._audio_index is not None:
            return self._audio_index.has_audio_for(word, variant)
        return False

    # ---------- 配置 ----------
    def set_audio_index(self, index: MddAudioIndex | None) -> None:
        self._audio_index = index

    def _pick_voices(self) -> None:
        """挑选英音(en_GB)/美音(en_US) 系统声音，供 TTS 回退时选择"""
        if self._tts is None:
            return
        try:
            for v in self._tts.availableVoices():
                loc = v.locale().name().lower()
                if loc.startswith("en_gb") and "gb" not in self._voices:
                    self._voices["gb"] = v
                elif loc.startswith("en_us") and "us" not in self._voices:
                    self._voices["us"] = v
        except Exception:
            pass

    # ---------- 发音 ----------
    def speak(self, word: str, variant: str = "") -> bool:
        """朗读单词。有真实音频则播放原声，否则 TTS。返回是否用了真实音频。"""
        self.stop()
        word = word.strip()
        if not word:
            return False
        if self._audio_index is not None:
            hit = self._audio_index.find(word, variant)
            if hit is not None:
                self._play_bytes(hit[1])
                self.last_source = "real"
                return True
        self._speak_tts(word, variant)
        self.last_source = "tts"
        return False

    def play_key(self, audio_key: str, fallback_word: str = "") -> bool:
        """播放指定音频 key；缺失时用 fallback_word 走 TTS。"""
        self.stop()
        if self._audio_index is not None:
            data = self._audio_index.get(audio_key)
            if data:
                self._play_bytes(data)
                self.last_source = "real"
                return True
        if fallback_word:
            self._speak_tts(fallback_word)
        self.last_source = "tts"
        return False

    def stop(self) -> None:
        try:
            if self._player is not None:
                self._player.stop()
            if self._tts is not None:
                self._tts.stop()
        except Exception:
            pass
        self._clean_tmp()

    # ---------- 内部 ----------
    def _speak_tts(self, word: str, variant: str = "") -> None:
        if self._tts is None:
            return
        voice = (
            self._voices.get(variant)
            or self._voices.get("gb")
            or self._voices.get("us")
        )
        if voice is not None:
            try:
                self._tts.setVoice(voice)
            except Exception:
                pass
        self._tts.say(word)

    def _play_bytes(self, data: bytes) -> None:
        """把音频字节写入临时文件并播放（QMediaPlayer）。"""
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3", prefix="funlex_")
            os.write(fd, data)
            os.close(fd)
            self._clean_tmp()
            self._last_tmp = path
            self._ensure_player()
            self._player.setSource(QUrl.fromLocalFile(path))
            self._player.play()
        except Exception as e:
            print(f"[PronounceHelper] playback failed: {e}")

    def _ensure_player(self) -> None:
        if self._player is None:
            self._audio_output = QAudioOutput(self)
            self._audio_output.setVolume(1.0)
            self._player = QMediaPlayer(self)
            self._player.setAudioOutput(self._audio_output)

    def _clean_tmp(self) -> None:
        if self._last_tmp and os.path.exists(self._last_tmp):
            try:
                os.remove(self._last_tmp)
            except OSError:
                pass
        self._last_tmp = None

    def source_label(self) -> str:
        """发音来源标注（UI 展示用）"""
        return "牛津原声" if self.last_source == "real" else "TTS 合成（非牛津原声）"
