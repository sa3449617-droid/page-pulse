"""Tests for the Page Pulse parser module."""

import pytest

from parser import (
    audit_url,
    _validate_url,
    InvalidURLError,
    TimeoutError,
    NonHTMLError,
    FetchError,
)


# ---------------------------------------------------------------------------
# Unit tests: URL validation  (pure logic, no network)
# ---------------------------------------------------------------------------

class TestValidateURL:
    def test_valid_https_url(self):
        assert _validate_url("https://example.com") == "https://example.com"

    def test_missing_scheme_adds_https(self):
        assert _validate_url("example.com") == "https://example.com"

    def test_valid_http_url(self):
        assert _validate_url("http://example.com") == "http://example.com"

    def test_empty_string_raises(self):
        with pytest.raises(InvalidURLError, match="must not be empty"):
            _validate_url("")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidURLError, match="must not be empty"):
            _validate_url("   ")

    def test_no_hostname_raises(self):
        with pytest.raises(InvalidURLError, match="valid hostname"):
            _validate_url("https://")

    def test_garbage_raises(self):
        with pytest.raises(InvalidURLError, match="valid URL"):
            _validate_url("not-a-url")

    def test_localhost_is_valid(self):
        result = _validate_url("http://localhost:8000")
        assert result == "http://localhost:8000"

    def test_ip_address_is_valid(self):
        result = _validate_url("http://127.0.0.1")
        assert result == "http://127.0.0.1"


# ---------------------------------------------------------------------------
# Integration tests: audit_url against real, stable targets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuditURLHappyPath:
    async def test_audits_example_dot_com(self):
        """Audit a stable public page and verify all report fields."""
        report = await audit_url("https://example.com")
        assert report["url"] == "https://example.com"
        assert report["status_code"] == 200
        assert isinstance(report["response_time_ms"], int)
        assert report["response_time_ms"] >= 0
        assert report["page_title"] is not None
        assert isinstance(report["page_title"], str)
        assert isinstance(report["meta_description"], (str, type(None)))
        assert isinstance(report["h1_count"], int)
        assert report["h1_count"] >= 1
        assert isinstance(report["images_missing_alt"], int)
        assert isinstance(report["word_count"], int)
        assert report["word_count"] >= 1

    async def test_audit_handles_trailing_whitespace(self):
        """URL with whitespace is normalised."""
        report = await audit_url("  https://example.com  ")
        assert report["status_code"] == 200

    async def test_url_with_query_params(self):
        """URLs with query parameters work correctly."""
        report = await audit_url("https://example.com?foo=bar")
        assert report["status_code"] == 200

    async def test_url_with_fragment(self):
        """URLs with fragments work correctly."""
        report = await audit_url("https://example.com#section")
        assert report["status_code"] == 200

    async def test_audit_returns_correct_types(self):
        """All returned fields have the expected Python types."""
        report = await audit_url("https://example.com")
        assert isinstance(report["url"], str)
        assert isinstance(report["status_code"], int)
        assert isinstance(report["response_time_ms"], int)
        assert isinstance(report["page_title"], str)
        assert isinstance(report["meta_description"], (str, type(None)))
        assert isinstance(report["h1_count"], int)
        assert isinstance(report["images_missing_alt"], int)
        assert isinstance(report["word_count"], int)


# ---------------------------------------------------------------------------
# Error-handling tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAuditURLErrors:
    async def test_invalid_url_raises(self):
        """Garbage URL raises InvalidURLError."""
        with pytest.raises(InvalidURLError):
            await audit_url("htp://")

    async def test_empty_url_raises(self):
        with pytest.raises(InvalidURLError):
            await audit_url("")

    async def test_whitespace_url_raises(self):
        with pytest.raises(InvalidURLError):
            await audit_url("   ")

    async def test_timeout_raises(self):
        """A URL that hangs should raise TimeoutError."""
        with pytest.raises(TimeoutError):
            await audit_url("http://10.255.255.1:1")

    async def test_non_html_response_raises(self):
        """A URL that returns non-HTML should raise NonHTMLError."""
        with pytest.raises(NonHTMLError):
            await audit_url(
                "https://www.python.org/static/img/python-logo.png"
            )

    async def test_nonexistent_domain_raises(self):
        """A domain that does not exist should raise FetchError."""
        with pytest.raises(FetchError):
            await audit_url(
                "https://this-domain-definitely-does-not-exist-123456789.com"
            )
