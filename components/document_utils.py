import hashlib
import re
from typing import Any, Dict


SOURCE_FALLBACK = "https://www.c40knowledgehub.org/"
TITLE_RE = re.compile(r"^\s*Title:\s*(.+?)(?:\s+Content:|$)", re.IGNORECASE | re.DOTALL)


def normalize_text(text: str) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    return compact.replace(" .", ".")


def extract_doc_title(text: str, fallback: str = "C40 Knowledge Hub document") -> str:
    raw_text = (text or "").strip()
    if not raw_text:
        return fallback

    match = TITLE_RE.search(raw_text)
    if match:
        title = normalize_text(match.group(1))
        if title:
            return title[:160]

    first_line = raw_text.splitlines()[0].strip()
    if first_line:
        return normalize_text(first_line)[:160]
    return fallback


def metadata_source(metadata: Dict[str, Any]) -> str:
    metadata = metadata or {}
    return metadata.get("source") or metadata.get("url") or metadata.get("file_path") or SOURCE_FALLBACK


def document_key(doc: Any) -> str:
    metadata = dict(getattr(doc, "metadata", {}) or {})
    for key in ("_doc_key", "doc_id", "id", "source_id"):
        value = metadata.get(key)
        if value:
            return str(value)

    content = getattr(doc, "page_content", "") or ""
    return hashlib.sha1(content.encode("utf-8")).hexdigest()
