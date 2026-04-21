import os
import json
import subprocess
from typing import Optional


class YTDLError(Exception):
    pass


SUPPORTED_PLATFORMS = [
    {"name": "YouTube", "key": "youtube", "domains": ["youtube.com", "youtu.be"]},
    {"name": "Twitter/X", "key": "twitter", "domains": ["twitter.com", "x.com"]},
    {"name": "Instagram", "key": "instagram", "domains": ["instagram.com"]},
    {"name": "TikTok", "key": "tiktok", "domains": ["tiktok.com"]},
    {"name": "Bilibili", "key": "bilibili", "domains": ["bilibili.com", "b23.tv"]},
    {"name": "抖音", "key": "douyin", "domains": ["douyin.com"]},
    {"name": "西瓜视频", "key": "xigua", "domains": ["ixigua.com"]},
    {"name": "微博", "key": "weibo", "domains": ["weibo.com", "weibo.cn"]},
    {"name": "小红书", "key": "xiaohongshu", "domains": ["xiaohongshu.com", "xhslink.com"]},
    {"name": "知乎", "key": "zhihu", "domains": ["zhihu.com"]},
    {"name": "爱奇艺", "key": "iqiyi", "domains": ["iqiyi.com"]},
    {"name": "腾讯视频", "key": "tencent", "domains": ["v.qq.com"]},
    {"name": "优酷", "key": "youku", "domains": ["youku.com"]},
]


class YTDLService:
    def __init__(self):
        self._yt_dlp = None

    def _check_yt_dlp(self):
        if self._yt_dlp is not None:
            return True
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self._yt_dlp = True
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            import yt_dlp
            self._yt_dlp = True
            return True
        except ImportError:
            pass

        self._yt_dlp = False
        return False

    def is_supported(self, url: str) -> Optional[str]:
        for platform in SUPPORTED_PLATFORMS:
            for domain in platform["domains"]:
                if domain in url:
                    return platform["key"]
        return None

    def get_video_info(self, url: str) -> dict:
        if not self._check_yt_dlp():
            raise YTDLError("yt-dlp 未安装，请运行: pip install yt-dlp")

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--dump-json",
                    "--no-download",
                    "--no-warnings",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = result.stderr[:200] if result.stderr else "未知错误"
                raise YTDLError(f"获取视频信息失败: {error_msg}")

            info = json.loads(result.stdout)
            return {
                "title": info.get("title", ""),
                "duration": info.get("duration", 0),
                "description": info.get("description", ""),
                "uploader": info.get("uploader", ""),
                "platform": info.get("extractor_key", "").lower(),
                "thumbnail": info.get("thumbnail", ""),
            }

        except json.JSONDecodeError:
            raise YTDLError("视频信息解析失败")
        except subprocess.TimeoutExpired:
            raise YTDLError("获取视频信息超时")
        except YTDLError:
            raise
        except Exception as e:
            raise YTDLError(f"获取视频信息失败: {str(e)}")

    def download(self, url: str, output_dir: str) -> str:
        if not self._check_yt_dlp():
            raise YTDLError("yt-dlp 未安装，请运行: pip install yt-dlp")

        os.makedirs(output_dir, exist_ok=True)

        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestaudio/best",
                    "--extract-audio",
                    "--audio-format", "mp3",
                    "--audio-quality", "4",
                    "-o", output_template,
                    "--no-warnings",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode != 0:
                error_msg = result.stderr[:200] if result.stderr else "未知错误"
                raise YTDLError(f"下载失败: {error_msg}")

            mp3_files = [f for f in os.listdir(output_dir) if f.endswith('.mp3')]
            if mp3_files:
                return os.path.join(output_dir, mp3_files[-1])

            all_files = os.listdir(output_dir)
            if all_files:
                return os.path.join(output_dir, all_files[-1])

            raise YTDLError("下载完成但未找到输出文件")

        except subprocess.TimeoutExpired:
            raise YTDLError("下载超时")
        except YTDLError:
            raise
        except Exception as e:
            raise YTDLError(f"下载失败: {str(e)}")

    def download_subtitles(self, url: str, output_dir: str) -> Optional[str]:
        if not self._check_yt_dlp():
            return None

        os.makedirs(output_dir, exist_ok=True)

        output_template = os.path.join(output_dir, "sub")

        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--write-subs",
                    "--write-auto-subs",
                    "--sub-langs", "zh,en",
                    "--skip-download",
                    "-o", output_template,
                    "--no-warnings",
                    url
                ],
                capture_output=True,
                text=True,
                timeout=120
            )

            for f in os.listdir(output_dir):
                if f.endswith('.vtt') or f.endswith('.srt'):
                    return os.path.join(output_dir, f)

            return None

        except Exception:
            return None


_ytdl_service_instance = None


def get_ytdl_service() -> YTDLService:
    global _ytdl_service_instance
    if _ytdl_service_instance is None:
        _ytdl_service_instance = YTDLService()
    return _ytdl_service_instance
