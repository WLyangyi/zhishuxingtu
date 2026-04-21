import os
import re
import subprocess
from typing import Optional, List


class SubtitleError(Exception):
    pass


class SubtitleSegment:
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text

    def to_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text
        }


class SubtitleService:
    def extract_subtitles(self, video_path: str) -> Optional[str]:
        if not os.path.exists(video_path):
            raise SubtitleError("视频文件不存在")

        srt_content = self._extract_embedded_srt(video_path)
        if srt_content:
            text = self._parse_srt(srt_content)
            if text.strip():
                return text

        ass_content = self._extract_embedded_ass(video_path)
        if ass_content:
            text = self._parse_ass(ass_content)
            if text.strip():
                return text

        return None

    def _extract_embedded_srt(self, video_path: str) -> Optional[str]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "s",
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return None

            import json
            probe = json.loads(result.stdout)
            streams = probe.get("streams", [])

            if not streams:
                return None

            for i, stream in enumerate(streams):
                codec_name = stream.get("codec_name", "")
                index = stream.get("index", 0)

                try:
                    extract_result = subprocess.run(
                        [
                            "ffmpeg",
                            "-i", video_path,
                            "-map", f"0:{index}",
                            "-f", "srt",
                            "-y",
                            "pipe:1"
                        ],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if extract_result.returncode == 0 and extract_result.stdout.strip():
                        return extract_result.stdout

                except (subprocess.TimeoutExpired, Exception):
                    continue

        except Exception:
            pass

        return None

    def _extract_embedded_ass(self, video_path: str) -> Optional[str]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "s",
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return None

            import json
            probe = json.loads(result.stdout)
            streams = probe.get("streams", [])

            for stream in streams:
                codec_name = stream.get("codec_name", "")
                if codec_name == "ass":
                    index = stream.get("index", 0)
                    try:
                        extract_result = subprocess.run(
                            [
                                "ffmpeg",
                                "-i", video_path,
                                "-map", f"0:{index}",
                                "-f", "ass",
                                "-y",
                                "pipe:1"
                            ],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )

                        if extract_result.returncode == 0 and extract_result.stdout.strip():
                            return extract_result.stdout

                    except (subprocess.TimeoutExpired, Exception):
                        continue

        except Exception:
            pass

        return None

    def _parse_srt(self, srt_content: str) -> str:
        segments = []
        blocks = re.split(r'\n\s*\n', srt_content.strip())

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                text_lines = lines[2:]
                text = ' '.join(text_lines).strip()
                if text and not text.startswith('['):
                    segments.append(text)

        return '\n'.join(segments)

    def _parse_ass(self, ass_content: str) -> str:
        segments = []
        in_events = False
        text_index = -1

        for line in ass_content.split('\n'):
            line = line.strip()

            if line == '[Events]':
                in_events = True
                continue

            if line.startswith('[') and in_events:
                break

            if in_events:
                if line.startswith('Format:'):
                    parts = [p.strip() for p in line[7:].split(',')]
                    if 'Text' in parts:
                        text_index = parts.index('Text')
                    continue

                if line.startswith('Dialogue:') and text_index >= 0:
                    parts = line[9:].split(',', text_index + 1)
                    if len(parts) > text_index:
                        text = parts[text_index].strip()
                        text = re.sub(r'\{[^}]*\}', '', text)
                        text = text.replace('\\N', ' ').replace('\\n', ' ')
                        text = text.strip()
                        if text:
                            segments.append(text)

        return '\n'.join(segments)


_subtitle_service_instance = None


def get_subtitle_service() -> SubtitleService:
    global _subtitle_service_instance
    if _subtitle_service_instance is None:
        _subtitle_service_instance = SubtitleService()
    return _subtitle_service_instance
