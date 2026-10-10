import logging
import re
from typing import Optional
from bs4 import BeautifulSoup
import httpx
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

MIN_VALID_TEXT_LENGTH = 100  # Threshold to ensure content is meaningful news text
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


async def fetch_and_clean_article_content(url: str, timeout: float = 6.0) -> Optional[str]:
    """
    Fetch the content of a news page URL and clean it up.
    Uses browser impersonation (curl_cffi) to bypass Cloudflare/Akamai bot detection,
    and falls back to reader proxy (r.jina.ai) if 403 or anti-bot blocks occur.
    Returns cleaned text string if successful, or None if parsing fails.
    """
    if not url or not url.startswith("http"):
        logger.warning(f"Invalid URL provided: {url}")
        return None

    # Step 1: Attempt direct fetch with browser TLS impersonation
    content = await _fetch_with_curl_cffi(url, timeout=timeout)
    if content:
        cleaned = clean_html_content(content)
        if cleaned and len(cleaned) >= MIN_VALID_TEXT_LENGTH and not is_blocked_or_error_content(cleaned):
            return cleaned

    # Step 2: Fallback to reader proxy for heavily protected news sites (e.g. 403s on Cloudflare/Akamai)
    logger.info(f"Direct fetch blocked or empty for {url}. Attempting reader fallback...")
    fallback_content = await _fetch_with_reader_fallback(url, timeout=timeout)
    if fallback_content:
        cleaned = _clean_markdown_or_text(fallback_content)
        if cleaned and len(cleaned) >= MIN_VALID_TEXT_LENGTH and not is_blocked_or_error_content(cleaned):
            return cleaned

    logger.warning(f"Unable to extract sufficient content for {url} (all methods failed, blocked by anti-bot, or content too short)")
    return None



async def _fetch_with_curl_cffi(url: str, timeout: float) -> Optional[str]:
    """Fetch using curl_cffi with Chrome 124 TLS fingerprinting to bypass 403 blocks."""
    try:
        async with AsyncSession(impersonate="chrome124") as session:
            response = await session.get(url, headers=HEADERS, timeout=timeout)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Fetch for {url} returned HTTP {response.status_code}")
                return None
    except Exception as e:
        logger.debug(f"Fetch error for {url}: {e}")
        return None


async def _fetch_with_reader_fallback(url: str, timeout: float) -> Optional[str]:
    """Fallback proxy using Jina AI reader engine for sites requiring headless rendering."""
    reader_url = f"https://r.jina.ai/{url}"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(reader_url)
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Reader fallback for {url} returned HTTP {response.status_code}")
                return None
    except Exception as e:
        logger.debug(f"Reader fallback error for {url}: {e}")
        return None


def clean_html_content(html_content: str) -> str:
    """
    Parse raw HTML content and remove scripts, styles, headers, footers, and non-article markup.
    Returns clean plain text formatted into paragraphs.
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    # Remove non-content elements
    unwanted_tags = [
        "script", "style", "nav", "header", "footer", "aside",
        "form", "noscript", "svg", "iframe", "button", "input",
        "select", "textarea", "meta", "link"
    ]
    for tag in soup(unwanted_tags):
        tag.decompose()

    # Priority 1: Extract from <article> or <main> container if present
    content_container = soup.find("article") or soup.find("main") or soup.find(id=re.compile(r"content|article|main", re.I))
    target = content_container if content_container else soup.body or soup

    # Extract text from paragraph tags or headers
    paragraphs = []
    for elem in target.find_all(["p", "h1", "h2", "h3", "h4"]):
        text = elem.get_text(separator=" ", strip=True)
        if len(text) > 30 and not _is_boilerplate(text):
            paragraphs.append(text)

    # Fallback if no clean paragraphs found
    if not paragraphs:
        raw_text = target.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in raw_text.splitlines() if len(line.strip()) > 30 and not _is_boilerplate(line)]
        paragraphs = lines

    cleaned_text = "\n\n".join(paragraphs)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    return cleaned_text.strip()


def _clean_markdown_or_text(text: str) -> str:
    """Clean markdown output from reader fallback."""
    if not text:
        return ""

    # Remove markdown image syntax ![...](...)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Remove metadata lines like "Title: ...", "URL Source: ..."
    lines = []
    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("Title:") or line_stripped.startswith("URL Source:") or line_stripped.startswith("Markdown Content:"):
            continue
        if len(line_stripped) > 25 and not _is_boilerplate(line_stripped):
            lines.append(line_stripped)

    cleaned = "\n\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _is_boilerplate(text: str) -> bool:
    """Detect common webpage boilerplate lines."""
    lowered = text.lower()
    boilerplate_keywords = [
        "cookie", "privacy policy", "terms of service", "all rights reserved",
        "subscribe to our newsletter", "sign in", "log in", "share on facebook",
        "follow us on twitter", "javascript must be enabled"
    ]
    return any(keyword in lowered for keyword in boilerplate_keywords)


def is_blocked_or_error_content(text: str) -> bool:
    """
    Detects if the scraped content is an anti-bot block page, CloudFront 403,
    Cloudflare challenge, or proxy error banner rather than authentic news reporting.
    """
    if not text or len(text.strip()) < MIN_VALID_TEXT_LENGTH:
        return True

    text_lower = text.lower()
    error_signatures = [
        "warning: target url returned error",
        "request blocked",
        "generated by cloudfront",
        "403: forbidden",
        "403 forbidden",
        "access denied",
        "attention required! | cloudflare",
        "cloudflare ray id",
        "cf-chl-bypass",
        "checking your browser before accessing",
        "verify you are human",
        "security check to access",
        "enable javascript and cookies",
        "we can't connect to the server for this app or website",
        "the page you requested could not be found",
        "404 not found",
        "502 bad gateway",
        "503 service unavailable",
        "504 gateway time-out"
    ]
    return any(sig in text_lower for sig in error_signatures)

