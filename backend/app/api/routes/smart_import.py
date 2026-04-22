import os
import json
import asyncio
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.note import Note
from app.models.tag import Tag
from app.api.deps import get_current_user
from app.schemas.response import Response
from app.services.import_task_store import get_import_task_store, ImportTask
from app.services.pdf_service import get_pdf_service, PDFParseError
from app.services.summarizer_service import get_summarizer_service
from app.services.import_history_service import get_import_history_service
from app.services.crawler_service import get_crawler_service, CrawlerError
from app.services.video_service import get_video_service, VideoError
from app.services.subtitle_service import get_subtitle_service
from app.services.whisper_service import get_whisper_service, WhisperError
from app.services.ytdlp_service import get_ytdl_service, YTDLError, SUPPORTED_PLATFORMS
from app.core.config import settings

router = APIRouter(prefix="/import", tags=["智能导入"])

MAX_FILE_SIZE = getattr(settings, 'IMPORT_MAX_FILE_SIZE', 209715200)
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/x-matroska", "video/avi", "video/quicktime"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov"}
TEMP_DIR = getattr(settings, 'IMPORT_TEMP_DIR', './temp/imports')


def _ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


def _format_note_content(result: dict, source_info: dict) -> str:
    parts = []

    parts.append(f"# {result.get('title', '导入文档')}")
    parts.append("")

    summary = result.get('summary', '')
    if summary:
        parts.append(f"## 摘要\n\n{summary}")
        parts.append("")

    key_points = result.get('key_points', [])
    if key_points:
        parts.append("## 关键要点\n")
        for point in key_points:
            parts.append(f"- {point}")
        parts.append("")

    parts.append("## 来源信息\n")
    source_type = source_info.get('type', '')
    if source_type == 'pdf':
        parts.append(f"- 类型：PDF 文档")
        if source_info.get('filename'):
            parts.append(f"- 文件名：{source_info['filename']}")
    elif source_type == 'web':
        parts.append(f"- 类型：网页")
        if source_info.get('url'):
            parts.append(f"- 链接：{source_info['url']}")
    elif source_type in ('video', 'video_url'):
        parts.append(f"- 类型：视频")
        if source_info.get('platform'):
            parts.append(f"- 平台：{source_info['platform']}")
        if source_info.get('duration'):
            minutes = source_info['duration'] // 60
            seconds = source_info['duration'] % 60
            parts.append(f"- 时长：{minutes}分{seconds}秒")
        if source_info.get('url'):
            parts.append(f"- 链接：{source_info['url']}")
        if source_info.get('filename'):
            parts.append(f"- 文件名：{source_info['filename']}")

    parts.append(f"- 导入时间：{source_info.get('imported_at', '')}")
    parts.append("")

    tags = result.get('tags', [])
    if tags:
        parts.append(f"标签：{', '.join(tags)}")

    return "\n".join(parts)


async def _process_pdf(task: ImportTask, file_path: str, filename: str):
    task_store = get_import_task_store()
    pdf_service = get_pdf_service()
    summarizer = get_summarizer_service()

    try:
        task_store.update_task(task.task_id, status="parsing", progress=10, progress_message="正在解析文件...")
        await asyncio.sleep(0.1)

        text = pdf_service.extract_text(file_path)

        task_store.update_task(task.task_id, status="extracting", progress=30, progress_message="正在提取内容...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="analyzing", progress=50, progress_message="正在分析内容...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="summarizing", progress=70, progress_message="正在生成摘要...")

        source_type_name = "PDF文档"
        result = summarizer.summarize(text, source_type_name)

        from app.services.import_task_store import SourceInfo, ImportResult
        source_info = SourceInfo(
            type="pdf",
            filename=filename,
            imported_at=task.created_at
        )
        import_result = ImportResult(
            title=result.get("title", filename.replace(".pdf", "")),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info
        )

        task_store.update_task(
            task.task_id,
            status="completed",
            progress=100,
            progress_message="处理完成",
            extracted_content=text,
            result=import_result
        )

    except PDFParseError as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=str(e),
            progress_message=str(e)
        )
    except Exception as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=f"处理失败: {str(e)}",
            progress_message=f"处理失败: {str(e)}"
        )
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


async def _process_url(task: ImportTask, url: str):
    task_store = get_import_task_store()
    crawler = get_crawler_service()
    summarizer = get_summarizer_service()

    try:
        task_store.update_task(task.task_id, status="parsing", progress=10, progress_message="正在访问网页...")
        await asyncio.sleep(0.1)

        text, page_title, resolved_url = crawler.extract_content(url)

        task_store.update_task(task.task_id, status="extracting", progress=30, progress_message="正在提取正文...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="analyzing", progress=50, progress_message="正在分析内容...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="summarizing", progress=70, progress_message="正在生成摘要...")

        result = summarizer.summarize(text, "网页")

        from app.services.import_task_store import SourceInfo, ImportResult
        source_info = SourceInfo(
            type="web",
            url=resolved_url,
            imported_at=task.created_at
        )
        import_result = ImportResult(
            title=result.get("title", page_title),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info
        )

        task_store.update_task(
            task.task_id,
            status="completed",
            progress=100,
            progress_message="处理完成",
            extracted_content=text,
            result=import_result
        )

    except CrawlerError as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=str(e),
            progress_message=str(e)
        )
    except Exception as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=f"处理失败: {str(e)}",
            progress_message=f"处理失败: {str(e)}"
        )


@router.get("/status/{task_id}")
async def stream_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该任务")

    async def event_generator():
        last_progress = -1
        retry_count = 0
        max_retries = 300

        while retry_count < max_retries:
            task = task_store.get_task(task_id)
            if task is None:
                data = json.dumps({"type": "error", "code": "TASK_NOT_FOUND", "message": "任务不存在"}, ensure_ascii=False)
                yield f"data: {data}\n\n"
                break

            if task.progress != last_progress or task.status in ("completed", "failed"):
                last_progress = task.progress

                if task.status == "completed":
                    result_data = None
                    if task.result:
                        result_data = {
                            "title": task.result.title,
                            "summary": task.result.summary,
                            "key_points": task.result.key_points,
                            "tags": task.result.tags,
                            "source_info": {
                                "type": task.result.source_info.type if task.result.source_info else task.source_type,
                                "url": task.result.source_info.url if task.result.source_info else None,
                                "filename": task.result.source_info.filename if task.result.source_info else None,
                                "duration": task.result.source_info.duration if task.result.source_info else None,
                                "platform": task.result.source_info.platform if task.result.source_info else None,
                                "imported_at": task.result.source_info.imported_at if task.result.source_info else None,
                            } if task.result.source_info else None
                        }
                    data = json.dumps({"type": "completed", "progress": 100, "result": result_data}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    break
                elif task.status == "failed":
                    data = json.dumps({"type": "error", "code": "PROCESSING_ERROR", "message": task.error or "处理失败"}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    break
                else:
                    data = json.dumps({"type": "progress", "progress": task.progress, "message": task.progress_message}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            await asyncio.sleep(0.5)
            retry_count += 1

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/url")
async def import_url(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入 URL")

    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请输入有效的 URL（以 http:// 或 https:// 开头）")

    task_store = get_import_task_store()
    task = task_store.create_task(
        user_id=current_user.id,
        source_type="url",
        source_path=url
    )

    asyncio.create_task(_process_url(task, url))

    return Response(data={
        "task_id": task.task_id,
        "url": url
    }, message="URL 提交成功，正在处理")


async def _process_video(task: ImportTask, file_path: str, filename: str):
    task_store = get_import_task_store()
    video_service = get_video_service()
    subtitle_service = get_subtitle_service()
    summarizer = get_summarizer_service()

    try:
        task_store.update_task(task.task_id, status="parsing", progress=10, progress_message="正在解析视频...")
        await asyncio.sleep(0.1)

        video_info = video_service.get_video_info(file_path)

        from app.services.import_task_store import VideoInfo
        task_video_info = VideoInfo(
            duration=video_info.duration,
            width=video_info.width,
            height=video_info.height,
            fps=video_info.fps,
            audio_tracks=video_info.audio_tracks,
            subtitle_tracks=video_info.subtitle_tracks
        )
        task_store.update_task(
            task.task_id,
            progress=20,
            progress_message="正在提取字幕...",
            video_info=task_video_info
        )
        await asyncio.sleep(0.1)

        text = subtitle_service.extract_subtitles(file_path)

        if text and text.strip():
            task_store.update_task(task.task_id, status="extracting", progress=40, progress_message="字幕提取成功，正在分析内容...")
            await asyncio.sleep(0.1)
        else:
            task_store.update_task(task.task_id, status="extracting", progress=40, progress_message="无字幕，尝试提取音频...")
            await asyncio.sleep(0.1)

            if video_info.audio_tracks > 0:
                task_store.update_task(task.task_id, progress=50, progress_message="正在提取音频...")

                audio_path = file_path.rsplit('.', 1)[0] + ".mp3"
                try:
                    video_service.extract_audio(file_path, audio_path)
                except VideoError as e:
                    task_store.update_task(
                        task.task_id,
                        status="failed",
                        progress=0,
                        error=f"音频提取失败: {str(e)}",
                        progress_message=f"音频提取失败: {str(e)}"
                    )
                    return

                task_store.update_task(task.task_id, progress=60, progress_message="正在使用 Whisper 转录音频...")

                try:
                    from app.services.whisper_service import get_whisper_service, WhisperError
                    whisper = get_whisper_service()
                    text = whisper.transcribe(audio_path)
                    task_store.update_task(task.task_id, progress=75, progress_message="转录完成，正在分析内容...")
                except WhisperError as e:
                    task_store.update_task(
                        task.task_id,
                        status="failed",
                        progress=0,
                        error=f"语音转录失败: {str(e)}",
                        progress_message=f"语音转录失败: {str(e)}"
                    )
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception:
                        pass
                    return
                except Exception as e:
                    task_store.update_task(
                        task.task_id,
                        status="failed",
                        progress=0,
                        error=f"语音转录失败: {str(e)}",
                        progress_message=f"语音转录失败: {str(e)}"
                    )
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception:
                        pass
                    return

                try:
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except Exception:
                    pass
            else:
                task_store.update_task(
                    task.task_id,
                    status="failed",
                    progress=0,
                    error="视频无字幕且无音频轨道",
                    progress_message="视频无字幕且无音频轨道"
                )
                return

        task_store.update_task(task.task_id, status="analyzing", progress=60, progress_message="正在分析内容...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="summarizing", progress=70, progress_message="正在生成摘要...")

        result = summarizer.summarize(text, "视频")

        from app.services.import_task_store import SourceInfo, ImportResult
        source_info = SourceInfo(
            type="video",
            filename=filename,
            duration=video_info.duration,
            imported_at=task.created_at
        )
        import_result = ImportResult(
            title=result.get("title", filename),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info
        )

        task_store.update_task(
            task.task_id,
            status="completed",
            progress=100,
            progress_message="处理完成",
            extracted_content=text,
            result=import_result
        )

    except VideoError as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=str(e),
            progress_message=str(e)
        )
    except Exception as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=f"处理失败: {str(e)}",
            progress_message=f"处理失败: {str(e)}"
        )
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


@router.post("/video")
async def import_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    filename = file.filename or ""
    ext = filename.lower().split('.')[-1] if '.' in filename else ""
    if ext not in ('mp4', 'mkv', 'avi', 'mov'):
        raise HTTPException(status_code=400, detail="仅支持 MP4/MKV/AVI/MOV 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件超过 {MAX_FILE_SIZE // 1024 // 1024}MB 限制")

    _ensure_temp_dir()

    task_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{task_id}_{filename}")

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    task_store = get_import_task_store()
    task = task_store.create_task(
        user_id=current_user.id,
        source_type="video",
        source_path=file_path
    )

    asyncio.create_task(_process_video(task, file_path, filename))

    return Response(data={
        "task_id": task.task_id,
        "filename": filename,
        "file_size": len(content)
    }, message="视频上传成功，正在处理")


async def _process_video_url(task: ImportTask, url: str, platform: str):
    task_store = get_import_task_store()
    ytdl = get_ytdl_service()
    subtitle_service = get_subtitle_service()
    whisper = get_whisper_service()
    summarizer = get_summarizer_service()

    temp_dir = os.path.join(TEMP_DIR, task.task_id)

    try:
        task_store.update_task(task.task_id, status="parsing", progress=10, progress_message="正在获取视频信息...")
        await asyncio.sleep(0.1)

        video_info = ytdl.get_video_info(url)

        text = None
        subtitle_path = None

        if platform == "bilibili":
            task_store.update_task(task.task_id, progress=20, progress_message="正在通过 B站 MCP 获取字幕...")
            await asyncio.sleep(0.1)

            try:
                from app.services.bilibili_mcp_service import get_bilibili_mcp_service
                bilibili_mcp = get_bilibili_mcp_service()
                mcp_subtitle = await bilibili_mcp.get_video_subtitles_async(url)
                if mcp_subtitle and mcp_subtitle.strip():
                    text = mcp_subtitle
                    task_store.update_task(task.task_id, status="extracting", progress=40, progress_message="B站 MCP 字幕获取成功，正在分析内容...")
                    await asyncio.sleep(0.1)
            except Exception as e:
                print(f"B站 MCP 字幕获取失败: {str(e)}")

        if not text:
            task_store.update_task(task.task_id, progress=25, progress_message="正在下载字幕...")
            await asyncio.sleep(0.1)

            subtitle_path = ytdl.download_subtitles(url, temp_dir)
            if subtitle_path:
                try:
                    with open(subtitle_path, 'r', encoding='utf-8', errors='ignore') as f:
                        sub_content = f.read()
                    if sub_content.endswith('.srt'):
                        text = subtitle_service._parse_srt(sub_content)
                    elif sub_content.endswith('.vtt'):
                        text = subtitle_service._parse_srt(sub_content)
                    else:
                        text = subtitle_service._parse_srt(sub_content)
                    if text and not text.strip():
                        text = None
                except Exception:
                    text = None

        if text and text.strip():
            task_store.update_task(task.task_id, status="extracting", progress=40, progress_message="字幕下载成功，正在分析内容...")
            await asyncio.sleep(0.1)
        else:
            task_store.update_task(task.task_id, status="extracting", progress=30, progress_message="无字幕，正在下载音频...")
            await asyncio.sleep(0.1)

            try:
                audio_path = ytdl.download(url, temp_dir)
            except YTDLError as e:
                task_store.update_task(
                    task.task_id,
                    status="failed",
                    progress=0,
                    error=f"下载失败: {str(e)}",
                    progress_message=f"下载失败: {str(e)}"
                )
                return

            task_store.update_task(task.task_id, progress=50, progress_message="正在使用 Whisper 转录音频...")

            try:
                text = await asyncio.to_thread(whisper.transcribe, audio_path)
                task_store.update_task(task.task_id, progress=70, progress_message="转录完成，正在分析内容...")
            except WhisperError as e:
                task_store.update_task(
                    task.task_id,
                    status="failed",
                    progress=0,
                    error=f"语音转录失败: {str(e)}",
                    progress_message=f"语音转录失败: {str(e)}"
                )
                return

        task_store.update_task(task.task_id, status="analyzing", progress=75, progress_message="正在分析内容...")
        await asyncio.sleep(0.1)

        task_store.update_task(task.task_id, status="summarizing", progress=80, progress_message="正在生成摘要...")

        result = summarizer.summarize(text, "视频")

        from app.services.import_task_store import SourceInfo, ImportResult
        source_info = SourceInfo(
            type="video_url",
            url=url,
            duration=int(video_info.get("duration", 0) or 0),
            platform=platform,
            imported_at=task.created_at
        )
        import_result = ImportResult(
            title=result.get("title", video_info.get("title", "")),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info
        )

        task_store.update_task(
            task.task_id,
            status="completed",
            progress=100,
            progress_message="处理完成",
            extracted_content=text,
            result=import_result
        )

    except YTDLError as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=str(e),
            progress_message=str(e)
        )
    except Exception as e:
        task_store.update_task(
            task.task_id,
            status="failed",
            progress=0,
            error=f"处理失败: {str(e)}",
            progress_message=f"处理失败: {str(e)}"
        )
    finally:
        import shutil
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass


@router.post("/video-url")
async def import_video_url(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="请输入视频链接")

    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="请输入有效的 URL")

    ytdl = get_ytdl_service()
    platform = ytdl.is_supported(url)
    if not platform:
        raise HTTPException(status_code=400, detail="不支持该视频平台")

    task_store = get_import_task_store()
    task = task_store.create_task(
        user_id=current_user.id,
        source_type="video_url",
        source_path=url
    )

    asyncio.create_task(_process_video_url(task, url, platform))

    return Response(data={
        "task_id": task.task_id,
        "url": url,
        "platform": platform
    }, message="视频链接提交成功，正在处理")


@router.get("/capabilities")
async def get_capabilities(
    current_user: User = Depends(get_current_user)
):
    return Response(data={
        "platforms": SUPPORTED_PLATFORMS
    })


@router.post("/regenerate")
async def regenerate_summary(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id")

    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作该任务")

    if not task.extracted_content:
        raise HTTPException(status_code=400, detail="无原始内容，无法重新生成")

    source_type_name = {
        "pdf": "PDF文档",
        "url": "网页",
        "video": "视频",
        "video_url": "视频"
    }.get(task.source_type, "文档")

    try:
        summarizer = get_summarizer_service()
        result = summarizer.summarize(task.extracted_content, source_type_name)

        from app.services.import_task_store import ImportResult
        source_info = task.result.source_info if task.result else None

        import_result = ImportResult(
            title=result.get("title", task.result.title if task.result else "导入文档"),
            summary=result.get("summary", ""),
            key_points=result.get("key_points", []),
            tags=result.get("tags", []),
            source_info=source_info
        )

        task_store.update_task(
            task.task_id,
            result=import_result
        )

        return Response(data={
            "title": import_result.title,
            "summary": import_result.summary,
            "key_points": import_result.key_points,
            "tags": import_result.tags
        }, message="重新生成成功")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新生成失败: {str(e)}")


@router.post("/suggest-category")
async def suggest_category(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id")

    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task or not task.result:
        raise HTTPException(status_code=404, detail="任务或结果不存在")

    from app.models.folder import Folder
    folders = db.query(Folder).filter(Folder.user_id == current_user.id).all()
    folder_list = [{"id": f.id, "name": f.name} for f in folders]

    if not folder_list:
        return Response(data={"folder_id": None, "reason": "暂无文件夹"}, message="无可用文件夹")

    try:
        summarizer = get_summarizer_service()
        suggestion = summarizer.suggest_category(task.result.summary, folder_list)
        return Response(data=suggestion, message="分类建议生成成功")
    except Exception as e:
        return Response(data={"folder_id": None, "reason": f"建议生成失败: {str(e)}"}, message="建议生成失败")


@router.post("/pdf")
async def import_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="仅支持 PDF 文件")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件超过 {MAX_FILE_SIZE // 1024 // 1024}MB 限制")

    _ensure_temp_dir()

    task_id = str(uuid.uuid4())
    file_path = os.path.join(TEMP_DIR, f"{task_id}_{file.filename}")

    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    task_store = get_import_task_store()
    task = task_store.create_task(
        user_id=current_user.id,
        source_type="pdf",
        source_path=file_path
    )

    asyncio.create_task(_process_pdf(task, file_path, file.filename))

    return Response(data={
        "task_id": task.task_id,
        "filename": file.filename,
        "file_size": len(content)
    }, message="PDF 上传成功，正在处理")


@router.get("/{task_id}")
async def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权访问该任务")

    result_data = None
    if task.result:
        result_data = {
            "title": task.result.title,
            "summary": task.result.summary,
            "key_points": task.result.key_points,
            "tags": task.result.tags,
            "source_info": {
                "type": task.result.source_info.type if task.result.source_info else task.source_type,
                "url": task.result.source_info.url if task.result.source_info else None,
                "filename": task.result.source_info.filename if task.result.source_info else None,
                "duration": task.result.source_info.duration if task.result.source_info else None,
                "platform": task.result.source_info.platform if task.result.source_info else None,
                "imported_at": task.result.source_info.imported_at if task.result.source_info else None,
            } if task.result.source_info else None
        }

    return Response(data={
        "task_id": task.task_id,
        "source_type": task.source_type,
        "status": task.status,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "result": result_data,
        "extracted_content": task.extracted_content[:5000] if task.extracted_content else None,
        "error": task.error if task.status == "failed" else None,
        "created_at": task.created_at,
        "updated_at": task.updated_at
    })


@router.post("/save")
async def save_as_note(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_id = body.get("task_id")
    if not task_id:
        raise HTTPException(status_code=400, detail="缺少 task_id")

    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作该任务")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成，无法保存")

    title = body.get("title", task.result.title if task.result else "导入文档")
    summary = body.get("summary", task.result.summary if task.result else "")
    key_points = body.get("key_points", task.result.key_points if task.result else [])
    tags = body.get("tags", task.result.tags if task.result else [])
    folder_id = body.get("folder_id")

    source_info = {}
    if task.result and task.result.source_info:
        source_info = {
            "type": task.result.source_info.type,
            "url": task.result.source_info.url,
            "filename": task.result.source_info.filename,
            "duration": task.result.source_info.duration,
            "platform": task.result.source_info.platform,
            "imported_at": task.result.source_info.imported_at,
        }

    result_data = {
        "title": title,
        "summary": summary,
        "key_points": key_points,
        "tags": tags,
    }
    note_content = _format_note_content(result_data, source_info)

    note = Note(
        title=title,
        content=note_content,
        folder_id=folder_id,
        user_id=current_user.id,
        linked_note_ids=json.dumps([])
    )

    if tags:
        for tag_name in tags:
            existing_tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if existing_tag:
                note.tags.append(existing_tag)

    db.add(note)
    db.commit()
    db.refresh(note)

    try:
        from app.services import get_vector_store, embedding_service
        from app.services.vector_store_adapter import get_vector_store_adapter

        vector_store = get_vector_store_adapter()
        if vector_store and embedding_service.available and note.content:
            chunks, vectors = embedding_service.embed_chunks(note.id, note.title, note.content)
            if chunks and len(vectors) > 0:
                vector_store.add_note_chunks(note.id, chunks, vectors)
    except Exception as e:
        print(f"Failed to add vector for imported note {note.id}: {e}")

    history_service = get_import_history_service()
    history_service.create_record(
        db=db,
        user_id=current_user.id,
        task_id=task_id,
        source_type=task.source_type,
        source_url=task.result.source_info.url if task.result and task.result.source_info else None,
        source_filename=task.result.source_info.filename if task.result and task.result.source_info else None,
        generated_title=title,
        note_id=note.id,
        status="completed"
    )

    task_store.delete_task(task_id)

    return Response(data={"note_id": note.id}, message="保存为笔记成功")


@router.get("/history/list")
async def get_import_history(
    source_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    history_service = get_import_history_service()
    items, total = history_service.get_history(
        db=db,
        user_id=current_user.id,
        source_type=source_type,
        page=page,
        page_size=page_size
    )

    history_list = []
    for item in items:
        history_list.append({
            "id": item.id,
            "task_id": item.task_id,
            "source_type": item.source_type,
            "source_url": item.source_url,
            "source_filename": item.source_filename,
            "duration": item.duration,
            "platform": item.platform,
            "generated_title": item.generated_title,
            "note_id": item.note_id,
            "status": item.status,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })

    return Response(data={
        "items": history_list,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task_store = get_import_task_store()
    task = task_store.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作该任务")

    if task.source_path and os.path.exists(task.source_path):
        try:
            os.remove(task.source_path)
        except Exception:
            pass

    task_store.delete_task(task_id)
    return Response(message="任务已删除")
