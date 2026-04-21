import os
from typing import Optional
from app.core.config import settings


class WhisperError(Exception):
    pass


class WhisperService:
    def __init__(self):
        self._model = None
        self._model_name = getattr(settings, 'WHISPER_MODEL', 'base')
        self._device = getattr(settings, 'WHISPER_DEVICE', 'cpu')
        self._compute_type = "int8" if self._device == "cpu" else "float16"

    def _load_model(self):
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type
            )
        except ImportError:
            raise WhisperError("faster-whisper 未安装，请运行: pip install faster-whisper")
        except Exception as e:
            raise WhisperError(f"Whisper 模型加载失败: {str(e)}")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        if not os.path.exists(audio_path):
            raise WhisperError("音频文件不存在")

        self._load_model()

        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts)

            if not full_text.strip():
                raise WhisperError("语音转录结果为空")

            return full_text

        except WhisperError:
            raise
        except Exception as e:
            raise WhisperError(f"语音转录失败: {str(e)}")

    def get_language(self, audio_path: str) -> Optional[str]:
        if not os.path.exists(audio_path):
            return None

        self._load_model()

        try:
            segments, info = self._model.transcribe(
                audio_path,
                beam_size=1,
                language=None
            )
            return info.language
        except Exception:
            return None


_whisper_service_instance = None


def get_whisper_service() -> WhisperService:
    global _whisper_service_instance
    if _whisper_service_instance is None:
        _whisper_service_instance = WhisperService()
    return _whisper_service_instance
