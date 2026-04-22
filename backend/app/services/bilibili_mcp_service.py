import os
import sys
import re
import json
import site

_user_site_packages = site.getusersitepackages()
if _user_site_packages and _user_site_packages not in sys.path:
    sys.path.insert(0, _user_site_packages)

from typing import Optional


class BilibiliMCPService:
    def __init__(self):
        self._credential = None
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return

        self._initialized = True

        try:
            from app.core.config import settings
            sessdata = getattr(settings, 'BILIBILI_SESSDATA', '')
            if sessdata:
                bili_jct = getattr(settings, 'BILIBILI_BILI_JCT', '')
                buvid3 = getattr(settings, 'BILIBILI_BUVID3', '')
                dedeuserid = getattr(settings, 'BILIBILI_DEDEUSERID', '')
                self.set_credential(sessdata, bili_jct, buvid3, dedeuserid)
                print(f"B站凭证已配置，将优先使用官方字幕")
        except ImportError:
            pass

    def set_credential(self, sessdata: str, bili_jct: str = None, buvid3: str = None, dedeuserid: str = None):
        try:
            from bilibili_api import Credential
            self._credential = Credential(
                sessdata=sessdata,
                bili_jct=bili_jct,
                buvid3=buvid3,
                dedeuserid=dedeuserid
            )
        except ImportError:
            print("bilibili_api library not found")
        except Exception as e:
            print(f"Failed to set credential: {e}")

    def _get_bvid_from_url(self, url: str) -> Optional[str]:
        patterns = [
            r'BV[A-Za-z0-9]+',
            r'bv[A-Za-z0-9]+',
            r'BV1[A-Za-z0-9]{10,}',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _parse_url_for_bvid(self, url: str) -> Optional[str]:
        match = re.search(r'/video/(BV[aA-Za-z0-9]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'(BV[aA-Za-z0-9]+)', url)
        if match:
            return match.group(1)
        return None

    async def get_video_subtitles_async(self, url: str) -> Optional[str]:
        self._ensure_initialized()

        bvid = self._get_bvid_from_url(url)
        if not bvid:
            bvid = self._parse_url_for_bvid(url)

        if not bvid:
            return None

        if not self._credential:
            return None

        try:
            import bilibili_api
            from bilibili_api import video

            v = video.Video(bvid=bvid, credential=self._credential)
            info = await v.get_info()
            pages = info.get('pages', [])

            if not pages:
                return None

            cid = pages[0].get('cid')
            if not cid:
                return None

            subtitle_info = await v.get_subtitle(cid=cid)

            if not subtitle_info:
                return None

            subtitles = subtitle_info.get('subtitles', [])

            for sub in subtitles:
                if isinstance(sub, dict):
                    subtitle_url = sub.get('subtitle_url')
                    if subtitle_url:
                        if not subtitle_url.startswith('http'):
                            subtitle_url = 'https:' + subtitle_url
                        content = await self._fetch_subtitle_content_async(subtitle_url)
                        if content:
                            return content

            zh_sub = None
            for sub in subtitles:
                if isinstance(sub, dict) and sub.get('lang') == 'zh-CN':
                    zh_sub = sub
                    break

            if zh_sub:
                subtitle_url = zh_sub.get('subtitle_url')
                if subtitle_url:
                    if not subtitle_url.startswith('http'):
                        subtitle_url = 'https:' + subtitle_url
                    return await self._fetch_subtitle_content_async(subtitle_url)

            if subtitles:
                subtitle_url = subtitles[0].get('subtitle_url')
                if subtitle_url:
                    if not subtitle_url.startswith('http'):
                        subtitle_url = 'https:' + subtitle_url
                    return await self._fetch_subtitle_content_async(subtitle_url)

            return None

        except ImportError:
            return None
        except Exception as e:
            print(f"Failed to get subtitles via bilibili_api: {str(e)}")
            return None

    async def _fetch_subtitle_content_async(self, url: str) -> Optional[str]:
        try:
            import urllib.request

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')

            data = json.loads(content)
            text_parts = []

            if isinstance(data, dict):
                body = data.get('body', [])
                if isinstance(body, list):
                    for item in body:
                        if isinstance(item, dict):
                            text = item.get('content_text', '') or item.get('content', '') or item.get('text', '')
                            if text:
                                text_parts.append(text)

            return '\n'.join(text_parts) if text_parts else None

        except Exception:
            return None


_bilibili_mcp_service_instance = None


def get_bilibili_mcp_service() -> BilibiliMCPService:
    global _bilibili_mcp_service_instance
    if _bilibili_mcp_service_instance is None:
        _bilibili_mcp_service_instance = BilibiliMCPService()
    return _bilibili_mcp_service_instance
