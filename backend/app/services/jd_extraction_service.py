from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}

BLOCKED_STATUS_CODES = {401, 403, 406, 429}


class JobDescriptionFetchError(Exception):
    """User-friendly JD fetch failure."""


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise JobDescriptionFetchError("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise JobDescriptionFetchError("URL hostname is missing.")
    ip = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
    if any(ip in net for net in PRIVATE_NETS):
        raise JobDescriptionFetchError("Private/internal URLs are blocked for security.")


async def fetch_job_description(url: str) -> dict[str, str]:
    """
    Extract job-description text from a public URL.

    Some job boards, including Wellfound/LinkedIn/Indeed at times, block automated
    server-side requests with 403 or require browser JavaScript. We try:
      1. direct request with browser-like headers
      2. Jina Reader fallback
    If both fail, raise a friendly message and let the user paste the JD manually.
    """
    validate_public_url(url)

    last_reason = "the page blocked automated extraction"

    # Strategy 1: direct fetch with browser-like headers.
    try:
        direct = await _fetch_direct(url)
        if _looks_like_job_description(direct["text"]):
            direct["source"] = "direct"
            return direct
        last_reason = "the page did not expose enough job-description text"
    except JobDescriptionFetchError as exc:
        last_reason = str(exc)
    except Exception as exc:
        last_reason = str(exc)

    # Strategy 2: reader fallback. This helps with many static pages but cannot
    # bypass authenticated/private pages or aggressive anti-bot protection.
    try:
        reader = await _fetch_via_jina_reader(url)
        if _looks_like_job_description(reader["text"]):
            reader["source"] = "reader_fallback"
            return reader
        last_reason = "the reader fallback also returned too little job-description text"
    except Exception as exc:
        last_reason = str(exc)

    host = urlparse(url).hostname or "this site"
    raise JobDescriptionFetchError(
        f"Could not automatically fetch this job post from {host}. Reason: {last_reason}. "
        "Many job boards block scrapers with 403 Forbidden or render content only in the browser. "
        "Please copy the job description from the page and paste it into the text box, then run analysis."
    )


async def _fetch_direct(url: str) -> dict[str, str]:
    async with httpx.AsyncClient(timeout=12, follow_redirects=True, max_redirects=4) as client:
        response = await client.get(url, headers=BROWSER_HEADERS)

    if response.status_code in BLOCKED_STATUS_CODES:
        raise JobDescriptionFetchError(f"HTTP {response.status_code} from target site")
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JobDescriptionFetchError(f"HTTP {response.status_code} from target site") from exc

    html = response.text[:2_000_000]
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else "Job Posting"
    text = clean_text(soup.get_text("\n", strip=True))
    return {"url": url, "title": title, "text": text}


async def _fetch_via_jina_reader(url: str) -> dict[str, str]:
    # Jina Reader accepts the source URL after this prefix and returns markdown.
    reader_url = f"https://r.jina.ai/http://r.jina.ai/http://{url}"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(reader_url, headers={"User-Agent": "AuraAnalyzeBot/1.0"})
    response.raise_for_status()
    text = clean_text(response.text)
    title = "Job Posting"
    first_line = next((line for line in text.splitlines() if line.lower().startswith("title:")), "")
    if first_line:
        title = first_line.replace("Title:", "", 1).strip() or title
    return {"url": url, "title": title, "text": text}


def clean_text(text: str) -> str:
    lines = []
    seen = set()
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if len(line) < 3:
            continue
        if line.lower() in {"apply", "home", "careers", "privacy policy", "terms", "sign in", "login"}:
            continue
        # remove extreme duplicate boilerplate
        key = line.lower()[:120]
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
    joined = "\n".join(lines)
    return joined[:12000]


def _looks_like_job_description(text: str) -> bool:
    low = (text or "").lower()
    if len(low) < 500:
        return False
    job_signals = [
        "responsibilities",
        "requirements",
        "qualifications",
        "experience",
        "skills",
        "what you'll do",
        "what you will do",
        "about the role",
        "job description",
        "apply",
    ]
    return sum(1 for signal in job_signals if signal in low) >= 2
