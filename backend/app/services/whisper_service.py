import os
import json
import time
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
        self._local_model_failed = False
        self._local_model_tried = False
        self._dashscope_api_key = None

    def _load_model(self) -> bool:
        if self._model is not None:
            return True

        if self._local_model_failed:
            return False

        if self._local_model_tried and self._model is None:
            return False

        self._local_model_tried = True

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type
            )
            return True
        except ImportError:
            self._local_model_failed = True
            print("Warning: faster-whisper 未安装，将使用云端语音转文字服务")
            return False
        except Exception as e:
            self._local_model_failed = True
            error_msg = str(e)
            if "getaddrinfo failed" in error_msg or "Hub" in error_msg or "download" in error_msg.lower():
                print("Warning: 本地 Whisper 模型不可用，将使用云端语音转文字服务")
            else:
                print(f"Warning: Whisper 模型加载失败: {error_msg}，将使用云端语音转文字服务")
            return False

    def _get_dashscope_api_key(self) -> str:
        if self._dashscope_api_key:
            return self._dashscope_api_key

        api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
        if not api_key:
            raise WhisperError("请在 .env 中配置 DASHSCOPE_API_KEY 以使用云端语音转文字服务")

        self._dashscope_api_key = api_key
        return api_key

    def _transcribe_with_dashscope(self, audio_path: str, language: Optional[str] = None) -> str:
        api_key = self._get_dashscope_api_key()

        audio_file_path = os.path.abspath(audio_path)
        if not os.path.exists(audio_file_path):
            raise WhisperError(f"音频文件不存在: {audio_file_path}")

        file_size = os.path.getsize(audio_file_path)
        if file_size > 2 * 1024 * 1024 * 1024:
            raise WhisperError("音频文件超过 2GB 限制")

        try:
            import urllib.request
            import urllib.parse

            boundary = '---PythonFormBoundary' + str(time.time()).replace('.', '')

            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()

            filename = os.path.basename(audio_file_path)
            if not any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.mp4', '.avi', '.mkv', '.mov']):
                filename = 'audio.mp3'

            body_parts = []
            body_parts.append(f'--{boundary}\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Type: audio/mpeg\r\n\r\n'.encode('utf-8'))
            body_parts.append(audio_data)
            body_parts.append(f'\r\n--{boundary}\r\n'.encode('utf-8'))
            body_parts.append(f'Content-Disposition: form-data; name="model"\r\n\r\n'.encode('utf-8'))
            body_parts.append(b'paraformer-v2')
            body_parts.append(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

            body = b''.join(body_parts)

            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'Content-Length': str(len(body))
            }

            submit_url = 'https://dashscope.aliyuncs.com/api/v1/services/asr/text-generation'
            req = urllib.request.Request(
                submit_url,
                data=body,
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                submit_result = json.loads(response.read().decode('utf-8'))

            status_code = submit_result.get("status_code") or submit_result.get("code")
            if status_code and status_code != 200 and status_code != 201:
                error_msg = submit_result.get("message", str(submit_result.get("code", "Unknown")))
                raise WhisperError(f"语音转文字提交失败: {error_msg}")

            task_id = submit_result.get("output", {}).get("task_id")
            if not task_id:
                task_id = submit_result.get("data", {}).get("task_id")

            if not task_id:
                raise WhisperError(f"语音转文字提交返回无效的task_id: {submit_result}")

            max_retries = 120
            retry_interval = 3

            for _ in range(max_retries):
                time.sleep(retry_interval)

                status_url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
                status_req = urllib.request.Request(
                    status_url,
                    headers={'Authorization': f'Bearer {api_key}'},
                    method='GET'
                )

                with urllib.request.urlopen(status_req, timeout=30) as response:
                    status_result = json.loads(response.read().decode('utf-8'))

                task_status = status_result.get("output", {}).get("task_status", "")
                if not task_status:
                    task_status = status_result.get("data", {}).get("status", "")

                if task_status == "SUCCEEDED":
                    results = status_result.get("output", {}).get("results", [])
                    if not results:
                        results = status_result.get("data", {}).get("results", [])

                    if results:
                        transcription_url = results[0].get("transcription_url")
                        if transcription_url:
                            with urllib.request.urlopen(transcription_url, timeout=30) as response:
                                transcription_result = json.loads(response.read().decode('utf-8'))

                            if transcription_result.get("transcripts"):
                                sentences = transcription_result["transcripts"][0].get("sentences", [])
                                text_parts = []
                                for sentence in sentences:
                                    text = sentence.get("text", "")
                                    if text:
                                        text_parts.append(text)
                                full_text = "".join(text_parts)
                                if full_text.strip():
                                    return full_text

                            if transcription_result.get("text"):
                                return transcription_result["text"]

                    raise WhisperError("语音转文字返回结果格式错误")

                elif task_status == "FAILED":
                    raise WhisperError("语音转文字任务失败")

            raise WhisperError("语音转文字超时")

        except WhisperError:
            raise
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ""
            raise WhisperError(f"语音转文字API请求失败: {e.code} - {error_body}")
        except Exception as e:
            raise WhisperError(f"语音转文字失败: {str(e)}")

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        if not os.path.exists(audio_path):
            raise WhisperError("音频文件不存在")

        if self._load_model() and self._model is not None:
            return self._transcribe_with_local_model(audio_path, language)

        return self._transcribe_with_dashscope(audio_path, language)

    def _transcribe_with_local_model(self, audio_path: str, language: Optional[str] = None) -> str:
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

        if not self._load_model() or self._model is None:
            return None

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