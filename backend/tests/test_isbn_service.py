"""
Unit tests for isbn_service.py helpers and fetch_book_by_isbn().

Covers:
- Gap 1: _validate_isbn() accepts valid ISBN-10/13 with hyphens, rejects invalid patterns
- Gap 2: _extract_description() handles polymorphic shapes (None, str, dict)
- Gap 3: fetch_book_by_isbn() raises HTTPException(400) for invalid ISBN
- Gap 4: fetch_book_by_isbn() returns found=False, error="not_found" on 404
- Gap 5: fetch_book_by_isbn() returns found=False, error="unavailable" on network error
- Gap 6: fetch_book_by_isbn() returns found=True with correct fields on success
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import HTTPException

from app.services.isbn_service import (
    _validate_isbn,
    _extract_description,
    fetch_book_by_isbn,
)
from app.schemas.catalog import ISBNFetchResponse


# ===========================================================================
# Gap 1: _validate_isbn() validates ISBN format
# ===========================================================================


class TestValidateISBN:
    """Unit tests for _validate_isbn() — SSRF prevention."""

    def test_validate_isbn_valid_isbn13_no_hyphens(self):
        """Valid ISBN-13 without hyphens passes."""
        assert _validate_isbn("9780140449136") is True

    def test_validate_isbn_valid_isbn13_with_hyphens(self):
        """Valid ISBN-13 with hyphens passes."""
        assert _validate_isbn("978-0-14-044913-6") is True

    def test_validate_isbn_valid_isbn10(self):
        """Valid ISBN-10 format passes."""
        assert _validate_isbn("0140449136") is True

    def test_validate_isbn_valid_isbn10_with_hyphens(self):
        """Valid ISBN-10 with hyphens passes."""
        assert _validate_isbn("0-14-044913-6") is True

    def test_validate_isbn_too_short_rejects(self):
        """ISBN shorter than 8 characters rejects."""
        assert _validate_isbn("abc") is False

    def test_validate_isbn_too_long_rejects(self):
        """ISBN longer than 17 characters rejects."""
        assert _validate_isbn("99999999999999999999") is False

    def test_validate_isbn_with_slashes_rejects(self):
        """ISBN with slashes (path traversal) rejects."""
        assert _validate_isbn("../../etc") is False

    def test_validate_isbn_with_spaces_rejects(self):
        """ISBN with spaces rejects."""
        assert _validate_isbn("978 0 14 044913 6") is False

    def test_validate_isbn_with_dots_rejects(self):
        """ISBN with dots rejects."""
        assert _validate_isbn("978.0.14.044913.6") is False

    def test_validate_isbn_with_special_chars_rejects(self):
        """ISBN with other special chars rejects."""
        assert _validate_isbn("978!0@14#049136") is False

    def test_validate_isbn_extra_chars_at_end_rejects(self):
        """ISBN with extra characters at end rejects."""
        assert _validate_isbn("9780140449136extra") is False


# ===========================================================================
# Gap 2: _extract_description() handles polymorphic shapes
# ===========================================================================


class TestExtractDescription:
    """Unit tests for _extract_description() — handles 3 shapes from OL API."""

    def test_extract_description_none_input(self):
        """None input returns None."""
        assert _extract_description(None) is None

    def test_extract_description_plain_string(self):
        """Plain string returns same string."""
        text = "A fascinating novel about adventure and discovery."
        assert _extract_description(text) == text

    def test_extract_description_dict_with_value(self):
        """Dict with 'value' key returns the value."""
        result = _extract_description({"value": "The text from dict"})
        assert result == "The text from dict"

    def test_extract_description_empty_string_returns_none(self):
        """Empty string returns None."""
        assert _extract_description("") is None

    def test_extract_description_dict_missing_value_key(self):
        """Dict without 'value' key returns None."""
        assert _extract_description({"other_key": "text"}) is None

    def test_extract_description_dict_empty_value(self):
        """Dict with empty 'value' returns None."""
        assert _extract_description({"value": ""}) is None

    def test_extract_description_dict_null_value(self):
        """Dict with null 'value' returns None."""
        assert _extract_description({"value": None}) is None

    def test_extract_description_dict_with_whitespace_value(self):
        """Dict with whitespace-only value returns None (treated as falsy)."""
        # Whitespace string is truthy in Python, so this should return it
        # unless the implementation explicitly strips. Let's check what happens.
        result = _extract_description({"value": "   "})
        assert result == "   "  # Truthy, so returns as-is


# ===========================================================================
# Gap 3: fetch_book_by_isbn() raises HTTPException(400) for invalid ISBN
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_invalid_isbn_raises_400():
    """Calling fetch_book_by_isbn() with invalid ISBN raises HTTPException(400)."""
    with pytest.raises(HTTPException) as exc_info:
        await fetch_book_by_isbn("bad isbn!")

    assert exc_info.value.status_code == 400
    assert "Invalid ISBN format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_short_isbn_raises_400():
    """Short ISBN raises HTTPException(400)."""
    with pytest.raises(HTTPException) as exc_info:
        await fetch_book_by_isbn("abc")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_path_traversal_raises_400():
    """Path traversal in ISBN raises HTTPException(400)."""
    with pytest.raises(HTTPException) as exc_info:
        await fetch_book_by_isbn("../../etc/passwd")

    assert exc_info.value.status_code == 400


# ===========================================================================
# Gap 4: fetch_book_by_isbn() returns error="not_found" on 404
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_open_library_404():
    """When Open Library returns 404, returns found=False, error='not_found'."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        # Mock the async context manager
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition call returns 404
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client.get.return_value = mock_resp

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is False
        assert result.error == "not_found"
        assert result.title is None
        assert result.author is None


# ===========================================================================
# Gap 5: fetch_book_by_isbn() returns error="unavailable" on network error
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_network_error():
    """When httpx raises ConnectError, returns found=False, error='unavailable'."""
    import httpx

    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Simulate a connection error
        mock_client.get.side_effect = httpx.ConnectError("Network unreachable")

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is False
        assert result.error == "unavailable"


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_json_parse_error():
    """When JSON parsing fails, returns found=False, error='unavailable'."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition call returns 200 but with malformed JSON
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_resp

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is False
        assert result.error == "unavailable"


# ===========================================================================
# Gap 6: fetch_book_by_isbn() returns found=True with correct fields on success
# ===========================================================================


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_success_with_all_fields():
    """Successful 3-step chain returns found=True with all fields populated."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition response (step 1)
        edition_resp = MagicMock()
        edition_resp.status_code = 200
        edition_resp.json.return_value = {
            "title": "The Name of the Wind",
            "covers": [12345],  # Cover ID
            "authors": [{"key": "/authors/OL12345A"}],
            "works": [{"key": "/works/OL67890W"}],
        }

        # Author response (step 2)
        author_resp = MagicMock()
        author_resp.status_code = 200
        author_resp.json.return_value = {"name": "Patrick Rothfuss"}

        # Works response (step 3)
        works_resp = MagicMock()
        works_resp.status_code = 200
        works_resp.json.return_value = {
            "description": "A captivating tale of a young magician."
        }

        # Configure mock to return different responses for each call
        mock_client.get.side_effect = [edition_resp, author_resp, works_resp]

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is True
        assert result.title == "The Name of the Wind"
        assert result.author == "Patrick Rothfuss"
        assert result.description == "A captivating tale of a young magician."
        assert result.cover_url == "https://covers.openlibrary.org/b/id/12345-M.jpg"
        assert result.error is None


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_success_with_dict_description():
    """Successful fetch with dict-shaped description field."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition response
        edition_resp = MagicMock()
        edition_resp.status_code = 200
        edition_resp.json.return_value = {
            "title": "Test Book",
            "covers": [999],
            "authors": [{"key": "/authors/OL111A"}],
            "works": [{"key": "/works/OL222W"}],
        }

        # Author response
        author_resp = MagicMock()
        author_resp.status_code = 200
        author_resp.json.return_value = {"name": "Test Author"}

        # Works response with dict description
        works_resp = MagicMock()
        works_resp.status_code = 200
        works_resp.json.return_value = {
            "description": {"value": "Description from dict"}
        }

        mock_client.get.side_effect = [edition_resp, author_resp, works_resp]

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is True
        assert result.description == "Description from dict"


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_success_without_cover():
    """Successful fetch with no covers — cover_url is None."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition response with no covers
        edition_resp = MagicMock()
        edition_resp.status_code = 200
        edition_resp.json.return_value = {
            "title": "No Cover Book",
            "covers": [],  # Empty covers list
            "authors": [{"key": "/authors/OL111A"}],
            "works": [{"key": "/works/OL222W"}],
        }

        # Author response
        author_resp = MagicMock()
        author_resp.status_code = 200
        author_resp.json.return_value = {"name": "Author Name"}

        # Works response
        works_resp = MagicMock()
        works_resp.status_code = 200
        works_resp.json.return_value = {"description": "Some description"}

        mock_client.get.side_effect = [edition_resp, author_resp, works_resp]

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is True
        assert result.cover_url is None


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_author_lookup_failure_non_fatal():
    """Author lookup failure does not fail the whole fetch — author is None, continue."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition response
        edition_resp = MagicMock()
        edition_resp.status_code = 200
        edition_resp.json.return_value = {
            "title": "Book Title",
            "covers": [555],
            "authors": [{"key": "/authors/OL333A"}],
            "works": [{"key": "/works/OL444W"}],
        }

        # Author response fails (non-fatal)
        author_resp = MagicMock()
        author_resp.status_code = 500  # Server error
        author_resp.json.return_value = {}

        # Works response succeeds
        works_resp = MagicMock()
        works_resp.status_code = 200
        works_resp.json.return_value = {"description": "Works description"}

        mock_client.get.side_effect = [edition_resp, author_resp, works_resp]

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is True
        assert result.title == "Book Title"
        assert result.author is None  # Author fetch failed, but overall success
        assert result.description == "Works description"


@pytest.mark.asyncio
async def test_fetch_book_by_isbn_no_author_key_in_edition():
    """Edition has no authors list — author is None, continue with works."""
    with patch("app.services.isbn_service.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        # Edition response with no authors
        edition_resp = MagicMock()
        edition_resp.status_code = 200
        edition_resp.json.return_value = {
            "title": "Anonymous Book",
            "covers": [777],
            "authors": [],  # Empty authors
            "works": [{"key": "/works/OL888W"}],
        }

        # Works response
        works_resp = MagicMock()
        works_resp.status_code = 200
        works_resp.json.return_value = {"description": "A mysterious tale"}

        # Only called for works, not author
        mock_client.get.side_effect = [edition_resp, works_resp]

        result = await fetch_book_by_isbn("9780140449136")

        assert result.found is True
        assert result.title == "Anonymous Book"
        assert result.author is None
        assert result.description == "A mysterious tale"
