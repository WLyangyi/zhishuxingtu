import os
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

from app.services.import_task_store import (
    get_import_task_store, ImportTask, ImportResult, SourceInfo, VideoInfo
)
from app.services.summarizer_service import get_summarizer_service
from app.services.pdf_service import get_pdf_service, PDFParseError
from app.services.crawler_service import get_crawler_service, CrawlerError
from app.services.video_service import get_video_service, VideoError
from app.services.subtitle_service import get_subtitle_service
from app.services.whisper_service import get_whisper_service, WhisperError
from app.services.ytdlp_service import get_ytdl_service, YTDLError
from app.services.file_helper import cleanup_temp_file, cleanup_temp_dir, TEMP_DIR


class ProgressManager:
    def __init__(self, task_store: "ImportTaskStore", task_id: str, auto_delay: float = 0.1):
        self._task_store = task_store
        self._task_id = task_id
        self._auto_delay = auto_delay

    async def update(self, status: str, progress: int, message: str):
        self._task_store.update_task(
            self._task_id,
            status=status,
            progress=progress,
            progress_message=message
        )
        if self._auto_delay > 0:
            await asyncio.sleep(self._auto_delay)

    def update_sync(self, progress: int, message: str, **kwargs):
        self._task_store.update_task(
            self._task_id,
            progress=progress,
            progress_message=message,
            **kwargs
        )

    def completed(self, text: str, result: ImportResult):
        self._task_store.update_task(
            self._task_id,
            status="completed",
            progress=100,
            progress_message="处理完成",
            extracted_content=text,
            result=result
        )

    def failed(self, error: str):
        self._task_store.update_task(
            self._task_id,
            status="failed",
            progress=0,
            error=error,
            progress_message=error
        )


class BaseImportOrchestrator(ABC):
    def __init__(self, task: ImportTask):
        self.task = task
        self.task_store = get_import_task_store()
        self.summarizer = get_summarizer_service()
        self.progress = ProgressManager(self.task_store, task.task_id)

    async def execute(self):
        try:
            text = await self._extract_content()
            result = await self._generate_summary(text)
            source_info = self._build_source_info()
            import_result = self._build_import_result(result, source_info)
            self.progress.completed(text, import_result)
        except Exception as e:
            self.progress.failed(self._format_error(e))
        finally:
            self._cleanup()

    @abstractmethod
    async def _extract_content(self) -> str:
        pass

    @abstractmethod
    def _build_source_info(self) -> SourceInfo:
        pass

    @abstractmethod
    def _get_default_title(self) -> str:
        pass

    @abstractmethod
    def _get_source_type_name(self) -> str:
        pass

    @abstractmethod
    def _cleanup(self):
        pass

    async def _generate_summary(self, text: str) -> dict:
        await self.progress.update("summarizing", 70, "正在生成摘要...")
        return self.summarizer.summarize(text, self._get_source_type_name())

    def _build_import_result(self, result: dict, source_info: SourceInfo) -> ImportResult:
        return ImportResult(
            title=result.get("title", self._get_default_title()),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info,
            content_type=result.get("content_type", ""),
            language_detected=result.get("language_detected", "zh")
        )

    def _format_error(self, e: Exception) -> str:
        error_msg = str(e)
        known_errors = (PDFParseError, CrawlerError, VideoError, WhisperError, YTDLError)
        if isinstance(e, known_errors):
            return error_msg
        return f"处理失败: {error_msg}"


class PDFImportOrchestrator(BaseImportOrchestrator):
    def __init__(self, task: ImportTask, file_path: str, filename: str):
        super().__init__(task)
        self.file_path = file_path
        self.filename = filename
        self.pdf_service = get_pdf_service()

    async def _extract_content(self) -> str:
        await self.progress.update("parsing", 10, "正在解析文件...")
        text = self.pdf_service.extract_text(self.file_path)
        await self.progress.update("extracting", 30, "正在提取内容...")
        await self.progress.update("analyzing", 50, "正在分析内容...")
        return text

    def _build_source_info(self) -> SourceInfo:
        return SourceInfo(
            type="pdf",
            filename=self.filename,
            imported_at=self.task.created_at
        )

    def _get_default_title(self) -> str:
        return self.filename.replace(".pdf", "")

    def _get_source_type_name(self) -> str:
        return "PDF文档"

    def _cleanup(self):
        cleanup_temp_file(self.file_path)


class URLImportOrchestrator(BaseImportOrchestrator):
    def __init__(self, task: ImportTask, url: str):
        super().__init__(task)
        self.url = url
        self.resolved_url = url
        self.page_title = ""
        self.crawler = get_crawler_service()

    async def _extract_content(self) -> str:
        await self.progress.update("parsing", 10, "正在访问网页...")
        text, page_title, resolved_url = self.crawler.extract_content(self.url)
        self.page_title = page_title
        self.resolved_url = resolved_url
        await self.progress.update("extracting", 30, "正在提取正文...")
        await self.progress.update("analyzing", 50, "正在分析内容...")
        return text

    def _build_source_info(self) -> SourceInfo:
        return SourceInfo(
            type="web",
            url=self.resolved_url,
            imported_at=self.task.created_at
        )

    def _get_default_title(self) -> str:
        return self.page_title

    def _get_source_type_name(self) -> str:
        return "网页"

    def _cleanup(self):
        pass


class VideoImportOrchestrator(BaseImportOrchestrator):
    def __init__(self, task: ImportTask, file_path: str, filename: str):
        super().__init__(task)
        self.file_path = file_path
        self.filename = filename
        self.video_service = get_video_service()
        self.subtitle_service = get_subtitle_service()
        self.video_info = None
        self._audio_path = None

    async def _extract_content(self) -> str:
        await self.progress.update("parsing", 10, "正在解析视频...")

        self.video_info = self.video_service.get_video_info(self.file_path)

        task_video_info = VideoInfo(
            duration=self.video_info.duration,
            width=self.video_info.width,
            height=self.video_info.height,
            fps=self.video_info.fps,
            audio_tracks=self.video_info.audio_tracks,
            subtitle_tracks=self.video_info.subtitle_tracks
        )
        self.progress.update_sync(20, "正在提取字幕...", video_info=task_video_info)

        text = self.subtitle_service.extract_subtitles(self.file_path)

        if text and text.strip():
            await self.progress.update("extracting", 40, "字幕提取成功，正在分析内容...")
            return text

        await self.progress.update("extracting", 40, "无字幕，尝试提取音频...")

        if self.video_info.audio_tracks <= 0:
            raise VideoError("视频无字幕且无音频轨道")

        self.progress.update_sync(50, "正在提取音频...")
        self._audio_path = self.file_path.rsplit('.', 1)[0] + ".mp3"
        self.video_service.extract_audio(self.file_path, self._audio_path)

        self.progress.update_sync(60, "正在使用 Whisper 转录音频...")

        whisper = get_whisper_service()
        text = await asyncio.to_thread(whisper.transcribe, self._audio_path)
        self.progress.update_sync(75, "转录完成，正在分析内容...")

        return text

    async def _generate_summary(self, text: str) -> dict:
        await self.progress.update("analyzing", 60, "正在分析内容...")
        await self.progress.update("summarizing", 70, "正在生成摘要...")
        return self.summarizer.summarize(text, self._get_source_type_name())

    def _build_source_info(self) -> SourceInfo:
        return SourceInfo(
            type="video",
            filename=self.filename,
            duration=self.video_info.duration if self.video_info else 0,
            imported_at=self.task.created_at
        )

    def _get_default_title(self) -> str:
        return self.filename

    def _get_source_type_name(self) -> str:
        return "视频"

    def _cleanup(self):
        if self._audio_path:
            cleanup_temp_file(self._audio_path)
        cleanup_temp_file(self.file_path)


class VideoURLImportOrchestrator(BaseImportOrchestrator):
    def __init__(self, task: ImportTask, url: str, platform: str):
        super().__init__(task)
        self.url = url
        self.platform = platform
        self.ytdl = get_ytdl_service()
        self.subtitle_service = get_subtitle_service()
        self.whisper = get_whisper_service()
        self.temp_dir = os.path.join(TEMP_DIR, task.task_id)
        self._video_info = None

    async def _extract_content(self) -> str:
        await self.progress.update("parsing", 10, "正在获取视频信息...")
        self._video_info = self.ytdl.get_video_info(self.url)

        text = await self._try_extract_subtitles()
        if text and text.strip():
            return text

        return await self._transcribe_audio()

    async def _try_extract_subtitles(self) -> Optional[str]:
        if self.platform == "bilibili":
            self.progress.update_sync(20, "正在通过 B站 MCP 获取字幕...")
            try:
                from app.services.bilibili_mcp_service import get_bilibili_mcp_service
                bilibili_mcp = get_bilibili_mcp_service()
                mcp_subtitle = await bilibili_mcp.get_video_subtitles_async(self.url)
                if mcp_subtitle and mcp_subtitle.strip():
                    await self.progress.update("extracting", 40, "B站 MCP 字幕获取成功，正在分析内容...")
                    return mcp_subtitle
            except Exception as e:
                logger.warning(f"B站 MCP 字幕获取失败: {str(e)}")

        self.progress.update_sync(25, "正在下载字幕...")

        subtitle_path = self.ytdl.download_subtitles(self.url, self.temp_dir)
        if subtitle_path:
            text = self._parse_subtitle_file(subtitle_path)
            if text and text.strip():
                await self.progress.update("extracting", 40, "字幕下载成功，正在分析内容...")
                return text

        return None

    def _parse_subtitle_file(self, subtitle_path: str) -> Optional[str]:
        try:
            with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.subtitle_service._parse_srt(content)
        except Exception:
            return None

    async def _transcribe_audio(self) -> str:
        await self.progress.update("extracting", 30, "无字幕，正在下载音频...")

        audio_path = self.ytdl.download(self.url, self.temp_dir)

        self.progress.update_sync(50, "正在使用 Whisper 转录音频...")

        text = await asyncio.to_thread(self.whisper.transcribe, audio_path)
        self.progress.update_sync(70, "转录完成，正在分析内容...")
        return text

    async def _generate_summary(self, text: str) -> dict:
        await self.progress.update("analyzing", 75, "正在分析内容...")
        await self.progress.update("summarizing", 80, "正在生成摘要...")
        return self.summarizer.summarize(text, self._get_source_type_name())

    def _build_source_info(self) -> SourceInfo:
        return SourceInfo(
            type="video_url",
            url=self.url,
            duration=int(self._video_info.get("duration", 0) or 0) if self._video_info else 0,
            platform=self.platform,
            imported_at=self.task.created_at
        )

    def _get_default_title(self) -> str:
        if self._video_info:
            return self._video_info.get("title", "")
        return ""

    def _get_source_type_name(self) -> str:
        return "视频"

    def _cleanup(self):
        cleanup_temp_dir(self.temp_dir)
