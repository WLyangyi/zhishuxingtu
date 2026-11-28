import uuid
from urllib.parse import urlsplit, urlunsplit

EXCERPT_MAX_CHARS = 500


def _excerpt(value):
    text = " ".join(str(value or "").split())
    return text[:EXCERPT_MAX_CHARS] + "…" if len(text) > EXCERPT_MAX_CHARS else text


def normalize_web_url(url):
    if not isinstance(url, str):
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ""
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, "")
    )


def build_web_sources(documents, session_id):
    sources = []
    by_url = {}
    for doc in documents or []:
        if not isinstance(doc, dict):
            continue
        url = normalize_web_url(doc.get("url"))
        if not url:
            continue
        body = doc.get("full_content") or ""
        if url not in by_url:
            source = {
                "source_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{session_id}:{url}")),
                "ordinal": len(sources) + 1,
                "title": doc.get("title") or "",
                "url": url,
                "excerpt": _excerpt(body or doc.get("snippet")),
                "site_name": doc.get("site_name") or "",
                "retrieved_at": doc.get("retrieved_at"),
                "fetched_at": doc.get("fetched_at"),
                "artifact_id": doc.get("artifact_id"),
                "truncated": bool(doc.get("truncated")),
                "content_state": (
                    "fetched" if body
                    else "fetch_failed" if doc.get("fetch_failed")
                    else "summary"
                ),
            }
            by_url[url] = source
            sources.append(source)
        elif body:
            by_url[url]["title"] = doc.get("title") or by_url[url]["title"]
            by_url[url]["excerpt"] = _excerpt(body)
            by_url[url]["site_name"] = doc.get("site_name") or by_url[url]["site_name"]
            by_url[url]["retrieved_at"] = doc.get("retrieved_at") or by_url[url]["retrieved_at"]
            by_url[url]["fetched_at"] = doc.get("fetched_at")
            by_url[url]["artifact_id"] = doc.get("artifact_id")
            by_url[url]["truncated"] = bool(doc.get("truncated"))
            by_url[url]["content_state"] = "fetched"
        elif doc.get("fetch_failed") and by_url[url]["content_state"] != "fetched":
            by_url[url]["content_state"] = "fetch_failed"
    return sources


def validate_web_sources(sources):
    if not isinstance(sources, list):
        return []
    valid = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        ordinal = source.get("ordinal")
        url = source.get("url")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
            continue
        if not isinstance(url, str) or not normalize_web_url(url):
            continue
        if source.get("content_state") not in {"summary", "fetched", "fetch_failed"}:
            continue
        valid.append(source)
    return valid


def render_web_sources(sources):
    lines = []
    for source in sources or []:
        title = " ".join(str(source.get("title") or "").split()) or source["url"]
        lines.append(f"[{source['ordinal']}] {title} {source['url']}")
    return "\n".join(lines)
