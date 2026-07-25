"""
Page Pulse — Core URL parsing and auditing logic.

This module handles fetching a URL, parsing the HTML response, and
extracting the metrics required by the audit report.
"""

import re
import time
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


# Timeout for HTTP requests (seconds)
HTTP_TIMEOUT = 15.0
# Maximum response body size we are willing to parse (5 MB)
MAX_BODY_BYTES = 5 * 1024 * 1024


class AuditError(Exception):
    """Base exception for audit failures."""
    pass


class InvalidURLError(AuditError):
    """Raised when the provided URL is syntactically invalid."""
    pass


class TimeoutError(AuditError):
    """Raised when the request times out."""
    pass


class NonHTMLError(AuditError):
    """Raised when the response is not HTML (e.g. PDF, JSON, image)."""
    pass


class FetchError(AuditError):
    """Raised when the HTTP request fails for any other reason."""
    pass


def _validate_url(url: str) -> str:
    """Validate and normalise a URL.

    Returns the normalised URL (with scheme if missing).
    Raises InvalidURLError if the URL is clearly invalid.
    """
    if not url or not url.strip():
        raise InvalidURLError("URL must not be empty.")

    url = url.strip()

    # If no scheme, default to https
    if not urlparse(url).scheme:
        url = "https://" + url

    parsed = urlparse(url)
    if not parsed.netloc:
        raise InvalidURLError(
            f"'{url}' does not contain a valid hostname."
        )
    # Basic check: host should have at least one dot, be localhost, or be an IP
    host = parsed.hostname or ""
    if "." not in host and host not in ("localhost",):
        # Allow IP addresses like 127.0.0.1 (already caught by dot check above)
        raise InvalidURLError(
            f"'{url}' does not appear to be a valid URL."
        )

    return url


async def audit_url(url: str) -> dict:
    """Audit a URL and return a structured report.

    Args:
        url: The URL to audit.

    Returns:
        A dictionary containing:
            - url: the normalised URL
            - status_code: HTTP status code
            - response_time_ms: response time in milliseconds
            - page_title: <title> content (or None)
            - meta_description: <meta name="description"> content (or None)
            - h1_count: number of <h1> elements
            - images_missing_alt: count of <img> tags without alt text
            - word_count: approximate number of visible words

    Raises:
        InvalidURLError: if the URL is invalid.
        TimeoutError: if the request times out.
        NonHTMLError: if the response is not HTML.
        FetchError: if the request fails.
    """
    normalised_url = _validate_url(url)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(HTTP_TIMEOUT),
    ) as client:
        try:
            start = time.monotonic()
            response = await client.get(normalised_url)
            elapsed_ms = round((time.monotonic() - start) * 1000)
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to '{normalised_url}' timed out after "
                f"{HTTP_TIMEOUT}s."
            )
        except httpx.InvalidURL:
            raise InvalidURLError(f"'{url}' is not a valid URL.")
        except httpx.RequestError as exc:
            raise FetchError(
                f"Failed to fetch '{normalised_url}': {exc}"
            )

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        raise NonHTMLError(
            f"Response is not HTML (content-type: {content_type}). "
            f"Status: {response.status_code}."
        )

    soup = BeautifulSoup(response.text, "html.parser")

    # --- Extract report fields ---

    # Page title
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else None

    # Meta description
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_description = (
        meta_desc_tag.get("content", "").strip()
        if meta_desc_tag and meta_desc_tag.get("content")
        else None
    )

    # H1 count
    h1_count = len(soup.find_all("h1"))

    # Images missing alt text
    images_missing_alt = sum(
        1 for img in soup.find_all("img")
        if not img.get("alt") or not img["alt"].strip()
    )

    # Approximate word count (visible text only)
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    visible_text = soup.get_text(separator=" ")
    visible_text = re.sub(r"\s+", " ", visible_text).strip()
    word_count = len(visible_text.split()) if visible_text else 0

    report = {
        "url": str(response.url),
        "status_code": response.status_code,
        "response_time_ms": elapsed_ms,
        "page_title": page_title,
        "meta_description": meta_description,
        "h1_count": h1_count,
        "images_missing_alt": images_missing_alt,
        "word_count": word_count,
    }

    return report
