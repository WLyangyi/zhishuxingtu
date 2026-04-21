import os
import subprocess
import json
from typing import Optional


class VideoError(Exception):
    pass


class VideoInfo:
    def __init__(self):
        self.duration = 0
        self.width = 0
        self.height = 0
        self.fps = 0.0
        self.audio_tracks = 0
        self.subtitle_tracks = 0

    def to_dict(self):
        return {
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "audio_tracks": self.audio_tracks,
            "subtitle_tracks": self.subtitle_tracks
        }


class VideoService:
    def __init__(self):
        self._ffmpeg = None

    def _check_ffmpeg(self):
        if self._ffmpeg is not None:
            return True
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._ffmpeg = True
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        self._ffmpeg = False
        return False

    def get_video_info(self, file_path: str) -> VideoInfo:
        if not os.path.exists(file_path):
            raise VideoError("视频文件不存在")

        info = VideoInfo()

        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    file_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise VideoError("无法获取视频信息")

            probe = json.loads(result.stdout)

            if "format" in probe:
                duration = probe["format"].get("duration")
                if duration:
                    info.duration = int(float(duration))

            if "streams" in probe:
                for stream in probe["streams"]:
                    codec_type = stream.get("codec_type", "")
                    if codec_type == "video":
                        info.width = int(stream.get("width", 0))
                        info.height = int(stream.get("height", 0))
                        r_frame_rate = stream.get("r_frame_rate", "0/1")
                        try:
                            num, den = r_frame_rate.split("/")
                            info.fps = float(num) / float(den) if float(den) > 0 else 0
                        except (ValueError, ZeroDivisionError):
                            info.fps = 0
                    elif codec_type == "audio":
                        info.audio_tracks += 1
                    elif codec_type == "subtitle":
                        info.subtitle_tracks += 1

        except json.JSONDecodeError:
            raise VideoError("视频信息解析失败")
        except subprocess.TimeoutExpired:
            raise VideoError("获取视频信息超时")
        except FileNotFoundError:
            raise VideoError("ffprobe 未安装，请先安装 ffmpeg")

        return info

    def extract_audio(self, video_path: str, output_path: str) -> str:
        if not self._check_ffmpeg():
            raise VideoError("ffmpeg 未安装，请先安装 ffmpeg")

        if not os.path.exists(video_path):
            raise VideoError("视频文件不存在")

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", video_path,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-q:a", "4",
                    "-y",
                    output_path
                ],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise VideoError(f"音频提取失败: {result.stderr[:200]}")

            if not os.path.exists(output_path):
                raise VideoError("音频提取失败，输出文件不存在")

            return output_path

        except subprocess.TimeoutExpired:
            raise VideoError("音频提取超时")

    def has_audio_track(self, file_path: str) -> bool:
        try:
            info = self.get_video_info(file_path)
            return info.audio_tracks > 0
        except Exception:
            return False


_video_service_instance = None


def get_video_service() -> VideoService:
    global _video_service_instance
    if _video_service_instance is None:
        _video_service_instance = VideoService()
    return _video_service_instance
