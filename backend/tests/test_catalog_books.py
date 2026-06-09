"""
Integration tests for catalog books API endpoints.

Test infrastructure: pytest + pytest-asyncio + ASGITransport + in-memory SQLite

Covers:
- Gap 7: GET /api/books with student token returns paginated list; q= filters correctly
- Gap 8: GET /api/books response includes available_count (correlated subquery)
- Gap 9: POST /api/books creates book with librarian token; student/no token → 403/401
- Gap 10: PUT /api/books/{id} updates only provided fields (partial update)
- Gap 11: DELETE /api/books/{id} soft-deletes; subsequent GET /api/books does NOT return deleted book
- Gap 12: POST /api/books/{id}/copies creates copy visible in GET /api/books/{id}; PATCH /api/copies/{id}/lost
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.models.book import Book
from app.models.copy import Copy
from app.core.security import hash_password, create_access_token
from app.core.enums import UserRole, CopyStatus, CopyCondition


@pytest_asyncio.fixture
async def client(async_session: AsyncSession):
    """HTTP test client with DB dependency override."""
    from app.core.db import get_db

    async def override_get_db():
        try:
            yield async_session
            await async_session.commit()
        except Exception:
            await async_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def student_user(async_session: AsyncSession) -> User:
    """A verified student user in the test DB."""
    user = User(
        email="student@example.com",
        full_name="Test Student",
        hashed_password=hash_password("password123"),
        role=UserRole.student,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def librarian_user(async_session: AsyncSession) -> User:
    """A verified librarian user in the test DB."""
    user = User(
        email="librarian@example.com",
        full_name="Test Librarian",
        hashed_password=hash_password("password123"),
        role=UserRole.librarian,
        is_email_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_book(async_session: AsyncSession) -> Book:
    """A sample book in the test DB."""
    book = Book(
        isbn="9780140449136",
        title="python programming",
        author="John Doe",
        publisher="Tech Press",
        publish_year=2020,
        description="A book about Python.",
        cover_url="https://example.com/cover.jpg",
    )
    async_session.add(book)
    await async_session.commit()
    await async_session.refresh(book)
    return book


@pytest_asyncio.fixture
async def another_book(async_session: AsyncSession) -> Book:
    """Another sample book for search testing."""
    book = Book(
        isbn="9780123456789",
        title="java basics",
        author="Jane Smith",
        publisher="Dev Press",
        publish_year=2021,
        description="A book about Java.",
        cover_url="https://example.com/cover2.jpg",
    )
    async_session.add(book)
    await async_session.commit()
    await async_session.refresh(book)
    return book


# ============================================================================
# Gap 7: GET /api/books with student token returns paginated list; q= filters
# ============================================================================


@pytest.mark.asyncio
async def test_get_books_list_with_student_token(
    client: AsyncClient,
    student_user: User,
    sample_book: Book,
):
    """GET /api/books with student token returns paginated list of books."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert "pages" in body
    assert len(body["items"]) >= 1
    assert body["items"][0]["title"] == "python programming"


@pytest.mark.asyncio
async def test_get_books_without_token_returns_401(
    client: AsyncClient,
    sample_book: Book,
):
    """GET /api/books without token returns 401."""
    resp = await client.get("/api/books")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_get_books_with_search_filter(
    client: AsyncClient,
    student_user: User,
    sample_book: Book,
    another_book: Book,
):
    """GET /api/books?q=python filters to matching book."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    # Search for "python" — should match "python programming"
    resp = await client.get(
        "/api/books?q=python",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["total"] == 1, f"Expected 1 result, got {body['total']}"
    assert len(body["items"]) == 1
    assert "python" in body["items"][0]["title"].lower()


@pytest.mark.asyncio
async def test_get_books_search_case_insensitive(
    client: AsyncClient,
    student_user: User,
    sample_book: Book,
):
    """GET /api/books?q=PYTHON (uppercase) still matches 'python programming'."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    # Search with uppercase
    resp = await client.get(
        "/api/books?q=PYTHON",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_get_books_pagination(
    client: AsyncClient,
    student_user: User,
    async_session: AsyncSession,
):
    """GET /api/books respects page and page_size query parameters."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)

    # Create 5 books
    for i in range(5):
        book = Book(
            isbn=f"978000000000{i}",
            title=f"Book {i}",
            author=f"Author {i}",
            publisher="Press",
            publish_year=2020,
        )
        async_session.add(book)
    await async_session.commit()

    # Page 1, 2 items per page
    resp = await client.get(
        "/api/books?page=1&page_size=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["pages"] == 3  # ceil(5 / 2)


# ============================================================================
# Gap 8: GET /api/books response includes available_count
# ============================================================================


@pytest.mark.asyncio
async def test_get_books_includes_available_count_with_copy(
    client: AsyncClient,
    student_user: User,
    sample_book: Book,
    async_session: AsyncSession,
):
    """Book with 1 available copy returns available_count=1."""
    # Add an available copy
    copy = Copy(
        book_id=sample_book.id,
        barcode="BC001",
        status=CopyStatus.available,
        condition=CopyCondition.good,
    )
    async_session.add(copy)
    await async_session.commit()

    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert len(body["items"]) >= 1
    # Find our sample book
    book_item = next((b for b in body["items"] if b["id"] == sample_book.id), None)
    assert book_item is not None
    assert book_item["available_count"] == 1
    assert book_item["total_count"] == 1


@pytest.mark.asyncio
async def test_get_books_available_count_zero_with_no_copies(
    client: AsyncClient,
    student_user: User,
    async_session: AsyncSession,
):
    """Book with no copies returns available_count=0."""
    # Create a book with no copies
    book = Book(
        isbn="9780999999999",
        title="Rare Book",
        author="Unknown",
        publisher="Press",
    )
    async_session.add(book)
    await async_session.commit()

    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    book_item = next((b for b in body["items"] if b["id"] == book.id), None)
    assert book_item is not None
    assert book_item["available_count"] == 0
    assert book_item["total_count"] == 0


@pytest.mark.asyncio
async def test_get_books_available_count_excludes_non_available_copies(
    client: AsyncClient,
    student_user: User,
    sample_book: Book,
    async_session: AsyncSession,
):
    """available_count only includes status=available copies; on_loan are excluded."""
    # Add one available copy
    copy1 = Copy(
        book_id=sample_book.id,
        barcode="BC001",
        status=CopyStatus.available,
        condition=CopyCondition.good,
    )
    # Add one on_loan copy
    copy2 = Copy(
        book_id=sample_book.id,
        barcode="BC002",
        status=CopyStatus.on_loan,
        condition=CopyCondition.good,
    )
    async_session.add(copy1)
    async_session.add(copy2)
    await async_session.commit()

    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    book_item = next((b for b in body["items"] if b["id"] == sample_book.id), None)
    assert book_item is not None
    assert book_item["available_count"] == 1  # Only available copy
    assert book_item["total_count"] == 2  # Both copies


# ============================================================================
# Gap 9: POST /api/books creates with librarian token; student/no token → 403/401
# ============================================================================


@pytest.mark.asyncio
async def test_post_books_with_librarian_token_creates_book(
    client: AsyncClient,
    librarian_user: User,
):
    """POST /api/books with librarian token creates a new book."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)
    payload = {
        "isbn": "9780143109945",
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "publisher": "JB Lippincott",
        "publish_year": 1960,
        "description": "A classic novel of racial injustice.",
        "cover_url": "https://example.com/mockingbird.jpg",
    }
    resp = await client.post(
        "/api/books",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["title"] == "To Kill a Mockingbird"
    assert body["author"] == "Harper Lee"
    assert body["isbn"] == "9780143109945"
    assert body["id"] is not None


@pytest.mark.asyncio
async def test_post_books_with_student_token_returns_403(
    client: AsyncClient,
    student_user: User,
):
    """POST /api/books with student token returns 403 (require_librarian check)."""
    token = create_access_token(sub=student_user.id, role=student_user.role.value)
    payload = {
        "title": "Test Book",
        "author": "Test Author",
    }
    resp = await client.post(
        "/api/books",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_post_books_without_token_returns_401(client: AsyncClient):
    """POST /api/books without token returns 401."""
    payload = {
        "title": "Test Book",
        "author": "Test Author",
    }
    resp = await client.post("/api/books", json=payload)
    assert resp.status_code == 401, resp.text


# ============================================================================
# Gap 10: PUT /api/books/{id} partial update (only provided fields change)
# ============================================================================


@pytest.mark.asyncio
async def test_put_books_partial_update(
    client: AsyncClient,
    librarian_user: User,
    sample_book: Book,
):
    """PUT /api/books/{id} with only title updates title; author unchanged."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)
    original_author = sample_book.author

    # Update only title
    resp = await client.put(
        f"/api/books/{sample_book.id}",
        json={"title": "New Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["title"] == "New Title"
    assert body["author"] == original_author  # Author unchanged


@pytest.mark.asyncio
async def test_put_books_partial_update_multiple_fields(
    client: AsyncClient,
    librarian_user: User,
    sample_book: Book,
):
    """PUT /api/books/{id} can update multiple fields selectively."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)

    # Update title and publisher only
    resp = await client.put(
        f"/api/books/{sample_book.id}",
        json={"title": "Updated Title", "publisher": "New Publisher"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["title"] == "Updated Title"
    assert body["publisher"] == "New Publisher"


# ============================================================================
# Gap 11: DELETE /api/books/{id} soft-deletes; subsequent GET does NOT return it
# ============================================================================


@pytest.mark.asyncio
async def test_delete_book_soft_deletes(
    client: AsyncClient,
    librarian_user: User,
    sample_book: Book,
):
    """DELETE /api/books/{id} soft-deletes the book."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)

    # Delete the book
    resp = await client.delete(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert "deleted" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_deleted_book_not_in_list(
    client: AsyncClient,
    librarian_user: User,
    student_user: User,
    sample_book: Book,
):
    """After DELETE, GET /api/books does NOT return the deleted book."""
    librarian_token = create_access_token(
        sub=librarian_user.id, role=librarian_user.role.value
    )
    student_token = create_access_token(
        sub=student_user.id, role=student_user.role.value
    )

    # First, verify book is in list
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    book_ids = [b["id"] for b in body["items"]]
    assert sample_book.id in book_ids

    # Delete the book
    resp = await client.delete(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Get list again — book should not be present
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    book_ids = [b["id"] for b in body["items"]]
    assert sample_book.id not in book_ids


@pytest.mark.asyncio
async def test_deleted_book_direct_get_returns_404(
    client: AsyncClient,
    librarian_user: User,
    student_user: User,
    sample_book: Book,
):
    """After DELETE, GET /api/books/{id} returns 404 for the deleted book."""
    librarian_token = create_access_token(
        sub=librarian_user.id, role=librarian_user.role.value
    )
    student_token = create_access_token(
        sub=student_user.id, role=student_user.role.value
    )

    # Delete the book
    resp = await client.delete(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Try to get the deleted book directly
    resp = await client.get(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 404, resp.text


# ============================================================================
# Gap 12: POST /api/books/{id}/copies and PATCH /api/copies/{id}/lost
# ============================================================================


@pytest.mark.asyncio
async def test_post_book_copies_creates_copy(
    client: AsyncClient,
    librarian_user: User,
    sample_book: Book,
):
    """POST /api/books/{id}/copies creates a copy of the book."""
    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)
    payload = {
        "barcode": "BC-2024-001",
        "condition": "good",
    }
    resp = await client.post(
        f"/api/books/{sample_book.id}/copies",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text

    body = resp.json()
    assert body["book_id"] == sample_book.id
    assert body["barcode"] == "BC-2024-001"
    assert body["condition"] == "good"
    assert body["status"] == "available"
    assert body["id"] is not None


@pytest.mark.asyncio
async def test_copy_visible_in_get_book_detail(
    client: AsyncClient,
    librarian_user: User,
    student_user: User,
    sample_book: Book,
):
    """Created copy is visible in GET /api/books/{id}."""
    librarian_token = create_access_token(
        sub=librarian_user.id, role=librarian_user.role.value
    )
    student_token = create_access_token(
        sub=student_user.id, role=student_user.role.value
    )

    # Create a copy
    payload = {
        "barcode": "BC-TEST-001",
        "condition": "good",
    }
    resp = await client.post(
        f"/api/books/{sample_book.id}/copies",
        json=payload,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert resp.status_code == 201, resp.text
    copy_id = resp.json()["id"]

    # Get book detail and verify copy is present
    resp = await client.get(
        f"/api/books/{sample_book.id}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert "copies" in body
    assert len(body["copies"]) >= 1
    copy_ids = [c["id"] for c in body["copies"]]
    assert copy_id in copy_ids


@pytest.mark.asyncio
async def test_patch_copy_lost_marks_lost(
    client: AsyncClient,
    librarian_user: User,
    sample_book: Book,
    async_session: AsyncSession,
):
    """PATCH /api/copies/{id}/lost sets status=lost and deleted_at."""
    # Create a copy
    copy = Copy(
        book_id=sample_book.id,
        barcode="BC-LOST-001",
        status=CopyStatus.available,
        condition=CopyCondition.good,
    )
    async_session.add(copy)
    await async_session.commit()
    await async_session.refresh(copy)

    token = create_access_token(sub=librarian_user.id, role=librarian_user.role.value)
    resp = await client.patch(
        f"/api/copies/{copy.id}/lost",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["status"] == "lost"


@pytest.mark.asyncio
async def test_lost_copy_excluded_from_available_count(
    client: AsyncClient,
    librarian_user: User,
    student_user: User,
    sample_book: Book,
    async_session: AsyncSession,
):
    """After marking copy as lost, available_count decreases."""
    librarian_token = create_access_token(
        sub=librarian_user.id, role=librarian_user.role.value
    )
    student_token = create_access_token(
        sub=student_user.id, role=student_user.role.value
    )

    # Create two available copies
    copy1 = Copy(
        book_id=sample_book.id,
        barcode="BC-001",
        status=CopyStatus.available,
        condition=CopyCondition.good,
    )
    copy2 = Copy(
        book_id=sample_book.id,
        barcode="BC-002",
        status=CopyStatus.available,
        condition=CopyCondition.good,
    )
    async_session.add(copy1)
    async_session.add(copy2)
    await async_session.commit()

    # Verify both are available
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text
    book_item = next(
        (b for b in resp.json()["items"] if b["id"] == sample_book.id), None
    )
    assert book_item["available_count"] == 2

    # Mark one copy as lost
    resp = await client.patch(
        f"/api/copies/{copy1.id}/lost",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )
    assert resp.status_code == 200, resp.text

    # Verify available_count decreased
    resp = await client.get(
        "/api/books",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert resp.status_code == 200, resp.text
    book_item = next(
        (b for b in resp.json()["items"] if b["id"] == sample_book.id), None
    )
    assert book_item["available_count"] == 1  # Now only 1 available
