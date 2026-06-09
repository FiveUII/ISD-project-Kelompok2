"""
Open Library ISBN fetch service.

Performs a 3-step chain against the Open Library API:
  1. Edition call  â€” GET /isbn/{isbn}.json         (title, covers, author/works keys)
  2. Author call   â€” GET /authors/{key}.json        (author name)
  3. Works call    â€” GET /works/{key}.json           (description)

Security (T-02-01 SSRF prevention):
  ISBN is validated server-side before any HTTPX call. Only [a-zA-Z0-9-] with
  length 8â€“17 is accepted; anything else raises HTTPException(400).

Rate-limit note:
  Open Library grants 3 req/sec to identified clients (vs 1 req/sec anonymous).
  OL_USER_AGENT is included on every request to obtain the higher limit.
"""
import re
from typing import Optional

import httpx
from fastapi import HTTPException

from app.schemas.catalog import ISBNFetchResponse

# Identify the application to Open Library so we get the 3 req/sec rate limit.
OL_USER_AGENT = "LibraryManagementSystem (faviannazmi@gmail.com)"

_OL_BASE = "https://openlibrary.org"

# Regex guards for Open Library key values — prevents SSRF via malicious keys
# in the API response (CR-02).
AUTHOR_KEY_RE = re.compile(r"^/authors/OL\d+A$")
WORK_KEY_RE = re.compile(r"^/works/OL\d+W$")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _validate_isbn(isbn: str) -> bool:
    """
    Return True if isbn contains only alphanumeric characters and hyphens,
    with a total length between 8 and 17 characters.

    This prevents SSRF: the raw value is interpolated into an external URL, so
    we reject anything that looks like a path traversal or URL injection.
    """
    return bool(re.match(r"^[a-zA-Z0-9-]{8,17}$", isbn))


def _extract_description(raw) -> Optional[str]:
    """
    Normalise the Open Library 'description' field which is polymorphic:
      - plain string  â†’  return as-is (or None if empty)
      - dict          â†’  return raw["value"] (or None if missing/empty)
      - None          â†’  return None

    See RISK-01 in the plan â€” all three shapes appear in production data.
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw or None
    if isinstance(raw, dict):
        return raw.get("value") or None
    return None


def _build_cover_url(covers: Optional[list]) -> Optional[str]:
    """
    Build an Open Library medium-size cover URL from the first cover ID.
    Returns None when the edition has no covers.
    """
    if not covers:
        return None
    cover_id = covers[0]
    return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"


# ---------------------------------------------------------------------------
# Main service function
# ---------------------------------------------------------------------------


async def fetch_book_by_isbn(isbn: str) -> ISBNFetchResponse:
    """
    Fetch bibliographic metadata for an ISBN from Open Library.

    Steps:
      1. Validate ISBN format (SSRF prevention â€” T-02-01).
      2. Fetch edition data at /isbn/{isbn}.json.
         - 404  â†’ ISBNFetchResponse(found=False, error="not_found")
         - other error / exception â†’ ISBNFetchResponse(found=False, error="unavailable")
      3. Fetch author name from /authors/{key}.json using the first author key
         in the edition. If absent or the call fails, author_name = None.
      4. Fetch description from /works/{key}.json using the first works key
         in the edition. If absent or the call fails, description = None.
      5. Return ISBNFetchResponse(found=True, ...) with all extracted fields.

    Any unhandled exception in the 3-step block is caught and returned as
    error="unavailable" (D-02 â€” network timeouts, JSON errors treated equally).
    """
    if not _validate_isbn(isbn):
        raise HTTPException(status_code=400, detail="Invalid ISBN format")

    headers = {"User-Agent": OL_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # ------------------------------------------------------------------
            # Step 1 â€” Edition call
            # ------------------------------------------------------------------
            edition_resp = await client.get(
                f"{_OL_BASE}/isbn/{isbn}.json",
                headers=headers,
            )

            if edition_resp.status_code == 404:
                return ISBNFetchResponse(found=False, error="not_found")

            if edition_resp.status_code != 200:
                return ISBNFetchResponse(found=False, error="unavailable")

            edition_data = edition_resp.json()

            # Extract scalar fields from the edition
            title: Optional[str] = edition_data.get("title")
            covers: list = edition_data.get("covers", [])
            cover_url = _build_cover_url(covers)

            # ------------------------------------------------------------------
            # Step 2 â€” Author call (RISK-02: author lives on /authors/, not edition)
            # ------------------------------------------------------------------
            author_name: Optional[str] = None
            authors_list = edition_data.get("authors", [])
            if authors_list:
                # Each entry is {"key": "/authors/OL...A"}
                author_key = authors_list[0].get("key", "")
                if author_key and AUTHOR_KEY_RE.match(author_key):
                    try:
                        author_resp = await client.get(
                            f"{_OL_BASE}{author_key}.json",
                            headers=headers,
                        )
                        if author_resp.status_code == 200:
                            author_name = author_resp.json().get("name")
                    except Exception:
                        # Author lookup failure is non-fatal â€” continue without name
                        author_name = None

            # ------------------------------------------------------------------
            # Step 3 â€” Works call (description lives on the work, not edition)
            # ------------------------------------------------------------------
            description: Optional[str] = None
            works_list = edition_data.get("works", [])
            if works_list:
                # Each entry is {"key": "/works/OL...W"}
                work_key = works_list[0].get("key", "")
                if work_key and WORK_KEY_RE.match(work_key):
                    try:
                        works_resp = await client.get(
                            f"{_OL_BASE}{work_key}.json",
                            headers=headers,
                        )
                        if works_resp.status_code == 200:
                            raw_desc = works_resp.json().get("description")
                            description = _extract_description(raw_desc)
                    except Exception:
                        # Works lookup failure is non-fatal â€” continue without description
                        description = None

            return ISBNFetchResponse(
                found=True,
                title=title,
                author=author_name,
                description=description,
                cover_url=cover_url,
            )

    except Exception:
        # Broad catch: network timeout, JSON parse error, connection refused, etc.
        # All treated as "API unavailable" (D-02).
        return ISBNFetchResponse(found=False, error="unavailable")
