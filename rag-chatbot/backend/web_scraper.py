"""Crawl sparrowi.com and produce Chunk objects for vector ingestion.

Extracts both text content and image metadata (alt text, figcaptions,
meta tags) so image-based content is also searchable.
"""

from __future__ import annotations

import hashlib
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from backend.chunker import Chunk
from backend.config import settings

MAX_CHUNK_CHARS = 1500

# URL slug corrections: map misleading URL slugs to accurate descriptions.
# The original blog post URL implies a Sparrow-Apple project, but Sparrow
# actually built a scale model of BKC for Jio World Convention Centre.
_URL_SLUG_CORRECTIONS = {
    "celebrating-a-milestone-apples-first-store-in-india-unveiled-at-bkc":
    "scale-model-of-bkc-for-jio-world-convention-centre",
}


def _correct_url(url: str) -> str:
    """Replace misleading URL slugs so chunk headers don't confuse the LLM."""
    for old, new in _URL_SLUG_CORRECTIONS.items():
        if old in url:
            url = url.replace(old, new)
    return url
STRIP_TAGS = {"script", "style", "noscript", "svg", "iframe"}

# Directories inside the local mirror that don't contain useful page content
_SKIP_DIRS = {
    "wp-content", "wp-includes", "wp-json", "wp-admin",
    "feed", "hts-cache", "cdn.jsdelivr.net",
    "www.googletagmanager.com", "fonts", "assets",
    "about-us-old",
}


def _make_chunk_id(url: str, index: int) -> str:
    """Create a deterministic chunk ID for a website chunk."""
    raw = f"website:{url}:{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _extract_meta(soup: BeautifulSoup) -> str:
    """Extract useful meta tags (og:title, og:description, description)."""
    parts = []

    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        parts.append(f"Page title: {og_title['content']}")

    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        parts.append(f"Description: {og_desc['content']}")

    if not og_desc:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            parts.append(f"Description: {meta_desc['content']}")

    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        parts.append(f"Featured image: {og_image['content']}")

    return "\n".join(parts)


def _extract_image_metadata(soup: BeautifulSoup) -> str:
    """Extract alt text, titles, and figcaptions from images."""
    image_info = []
    seen = set()

    # Get all image alt text and titles
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        title = (img.get("title") or "").strip()
        # Skip generic/empty alt text
        if alt and alt.lower() not in ("", "logo", "icon", "image", "img", "photo"):
            if alt not in seen:
                image_info.append(alt)
                seen.add(alt)
        if title and title not in seen:
            image_info.append(title)
            seen.add(title)

    # Get figcaptions
    for fig in soup.find_all("figcaption"):
        caption = fig.get_text(strip=True)
        if caption and caption not in seen:
            image_info.append(caption)
            seen.add(caption)

    if not image_info:
        return ""

    return "Image descriptions: " + " | ".join(image_info)


def _extract_text(html: str) -> str:
    """Extract clean text from HTML, including image metadata."""
    soup = BeautifulSoup(html, "html.parser")

    # Extract meta and image info BEFORE stripping tags
    meta_text = _extract_meta(soup)
    image_text = _extract_image_metadata(soup)

    # Remove unwanted elements
    for tag in soup.find_all(STRIP_TAGS):
        tag.decompose()

    # Also strip nav/footer/header from the main content extraction
    for tag in soup.find_all(["nav", "footer", "header"]):
        tag.decompose()

    # Prefer <main> content, fall back to <body>
    main = soup.find("main")
    container = main if main else soup.find("body")
    if not container:
        return ""

    text = container.get_text(separator="\n", strip=True)

    # Collapse multiple blank lines
    lines = [line.strip() for line in text.splitlines()]
    cleaned = []
    prev_blank = False
    for line in lines:
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    body_text = "\n".join(cleaned).strip()

    # Combine body text with meta and image info
    parts = []
    if meta_text:
        parts.append(meta_text)
    if body_text:
        parts.append(body_text)
    if image_text:
        parts.append(image_text)

    return "\n\n".join(parts)


def _split_text(text: str, url: str) -> list[Chunk]:
    """Split text into chunks of up to MAX_CHUNK_CHARS."""
    if not text:
        return []
    url = _correct_url(url)

    chunks = []
    paragraphs = text.split("\n\n")
    current_parts: list[str] = []
    current_len = 0
    chunk_idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # If adding this paragraph would exceed the limit, flush current
        if current_len + len(para) + 1 > MAX_CHUNK_CHARS and current_parts:
            chunk_text = f"[sparrowi.com — {url}]\n" + "\n\n".join(current_parts)
            chunks.append(Chunk(
                id=_make_chunk_id(url, chunk_idx),
                text=chunk_text,
                table="sparrowi.com",
                chunk_type="website",
                url=url,
            ))
            chunk_idx += 1
            current_parts = []
            current_len = 0
        current_parts.append(para)
        current_len += len(para) + 1

    # Flush remaining
    if current_parts:
        chunk_text = f"[sparrowi.com — {url}]\n" + "\n\n".join(current_parts)
        chunks.append(Chunk(
            id=_make_chunk_id(url, chunk_idx),
            text=chunk_text,
            table="sparrowi.com",
            chunk_type="website",
            url=url,
        ))

    return chunks


def _is_same_domain(url: str, base_domain: str) -> bool:
    """Check if URL belongs to the same domain."""
    parsed = urlparse(url)
    return parsed.netloc == base_domain or parsed.netloc == ""


def crawl() -> list[Chunk]:
    """BFS crawl from the configured base URL, returning Chunk objects.

    Uses synchronous httpx since this runs inside a FastAPI endpoint
    that will be called via asyncio.to_thread or similar.
    """
    base_url = settings.scraper_base_url
    max_pages = settings.scraper_max_pages
    timeout = settings.scraper_timeout

    base_parsed = urlparse(base_url)
    base_domain = base_parsed.netloc

    visited: set[str] = set()
    queue: deque[str] = deque([base_url])
    all_chunks: list[Chunk] = []

    print(f"[Scraper] Starting crawl from {base_url} (max {max_pages} pages)")

    while queue and len(visited) < max_pages:
        url = queue.popleft()

        # Normalize URL (strip fragment and trailing slash for dedup)
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if normalized in visited:
            continue

        # Skip non-HTML resources
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in (
            ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp",
            ".pdf", ".zip", ".mp4", ".mp3", ".css", ".js",
            ".ico", ".woff", ".woff2", ".ttf", ".eot",
        )):
            continue

        visited.add(normalized)

        try:
            resp = httpx.get(url, timeout=timeout, follow_redirects=True, headers={
                "User-Agent": "SparrowiBot/1.0 (internal content indexer)"
            })
            if resp.status_code != 200:
                print(f"[Scraper] Skipping {url} (status {resp.status_code})")
                continue

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            html = resp.text
        except Exception as e:
            print(f"[Scraper] Error fetching {url}: {e}")
            continue

        # Extract text (including image metadata) and create chunks
        text = _extract_text(html)
        if text and len(text) > 50:  # Skip near-empty pages
            chunks = _split_text(text, url)
            all_chunks.extend(chunks)
            print(f"[Scraper] {url} -> {len(chunks)} chunks")

        # Find links to crawl
        soup = BeautifulSoup(html, "html.parser")
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            absolute_url = urljoin(url, href)
            abs_parsed = urlparse(absolute_url)
            # Only follow same-domain HTTP(S) links
            if abs_parsed.scheme in ("http", "https") and _is_same_domain(absolute_url, base_domain):
                clean_url = f"{abs_parsed.scheme}://{abs_parsed.netloc}{abs_parsed.path.rstrip('/')}"
                if clean_url not in visited:
                    queue.append(absolute_url)

    print(f"[Scraper] Crawl complete: {len(visited)} pages visited, {len(all_chunks)} chunks created")
    return all_chunks


def crawl_mirror(mirror_dir: str | Path) -> list[Chunk]:
    """Walk the local mirror directory and produce Chunk objects.

    Reuses _extract_text and _split_text so the output is identical in
    format to what crawl() produces for live pages.
    """
    mirror_path = Path(mirror_dir)
    if not mirror_path.is_dir():
        print(f"[Mirror] Directory not found: {mirror_path}")
        return []

    all_chunks: list[Chunk] = []

    for html_file in mirror_path.rglob("*.html"):
        # Skip non-content directories
        rel_parts = html_file.relative_to(mirror_path).parts
        if any(part in _SKIP_DIRS for part in rel_parts):
            continue

        try:
            html = html_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[Mirror] Error reading {html_file}: {e}")
            continue

        text = _extract_text(html)
        if not text or len(text) < 50:
            continue

        # Convert file path to a website URL for chunk metadata
        rel = html_file.relative_to(mirror_path)
        # e.g.  www.sparrowi.com/about-us-old/index.html  →  https://www.sparrowi.com/about-us-old/
        url_path = str(rel).replace("\\", "/")
        if url_path.endswith("/index.html"):
            url_path = url_path[: -len("index.html")]
        # The mirror root folder is the domain name (www.sparrowi.com)
        url = f"https://{url_path}"

        chunks = _split_text(text, url)
        all_chunks.extend(chunks)

    print(f"[Mirror] Crawl complete: {len(all_chunks)} chunks from local mirror")
    return all_chunks
