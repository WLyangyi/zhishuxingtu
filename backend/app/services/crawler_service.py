import httpx
from typing import Optional


class CrawlerError(Exception):
    pass


class CrawlerService:
    def __init__(self):
        self._trafilatura = None
        self.timeout = 30.0

    def _get_trafilatura(self):
        if self._trafilatura is None:
            try:
                import trafilatura
                self._trafilatura = trafilatura
            except ImportError:
                raise CrawlerError("trafilatura 未安装，请运行: pip install trafilatura")
        return self._trafilatura

    def _fetch_html(self, url: str) -> Optional[str]:
        trafilatura = self._get_trafilatura()

        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded and len(downloaded) > 500:
                return downloaded
        except Exception:
            pass

        try:
            with httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                }
            ) as client:
                response = client.get(url)
                if response.status_code < 400:
                    return response.text
        except Exception:
            pass

        return None

    def extract_content(self, url: str, max_chars: int = 50000) -> tuple:
        trafilatura = self._get_trafilatura()

        downloaded = self._fetch_html(url)

        if downloaded is None:
            raise CrawlerError("无法访问该网页，请检查URL是否正确")

        try:
            metadata = trafilatura.bare_extraction(downloaded, include_formatting=False, include_links=False)
            if metadata is not None:
                if hasattr(metadata, 'as_dict'):
                    metadata = metadata.as_dict()
                elif hasattr(metadata, '__dict__'):
                    metadata = {k: v for k, v in metadata.__dict__.items() if not k.startswith('_')}
        except Exception:
            metadata = None

        try:
            text = trafilatura.extract(downloaded, include_formatting=False, include_links=False)
        except Exception as e:
            raise CrawlerError(f"无法提取网页内容: {str(e)}")

        if not text or not text.strip():
            raise CrawlerError("无法提取网页正文，可能是登录页或纯图片页面")

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[内容已截断，原文过长]"

        title = ""
        url_source = url
        if metadata:
            title = metadata.get("title", "") or ""
            url_source = metadata.get("url", url) or url

        if not title:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                title = parsed.netloc or url
            except Exception:
                title = url

        return text, title, url_source

    def is_accessible(self, url: str) -> bool:
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                response = client.head(url)
                return response.status_code < 400
        except Exception:
            return False


_crawler_service_instance = None


def get_crawler_service() -> CrawlerService:
    global _crawler_service_instance
    if _crawler_service_instance is None:
        _crawler_service_instance = CrawlerService()
    return _crawler_service_instance
