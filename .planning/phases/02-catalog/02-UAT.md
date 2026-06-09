---
status: complete
phase: 02-catalog
source: 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md
started: 2026-06-09T00:00:00Z
updated: 2026-06-09T13:00:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running containers. Run `docker compose up --build` from scratch. Backend boots without errors, Alembic migrations run (including 0003 index migration), frontend dev server (or Nginx) serves the app, and hitting /api/health (or the login page) returns a live response with no crash logs in the container output.
result: pass

### 2. NavBar and Shell Layout
expected: After logging in, every page shows the NavBar at the top: logo/link on the left, role-aware nav links (Catalog visible to all; Manage Books visible to librarians only), and a Logout button on the right. The main content area renders below the nav. Background is light gray (bg-gray-50).
result: pass

### 3. Auth Route Guard — Redirect to Login
expected: Navigating to /catalog or /librarian/books without being logged in redirects to /login. After logging in, the user lands on the originally requested page (or /catalog).
result: pass

### 4. Role Route Guard — Librarian-only Routes
expected: A student account navigating to /librarian/books is redirected to /catalog instead of seeing the librarian UI. No error page — clean redirect.
result: pass

### 5. Student Catalog Search — Results with Availability
expected: On the /catalog page, typing a title or author in the search box and pressing Enter (or clicking Search) fetches matching books. Each result card shows title, author, ISBN, a description snippet, and an AvailabilityBadge: green "X available" when copies exist, gray "0 available" when none.
result: pass

### 6. Student Catalog Search — Empty States
expected: Landing on /catalog with no search query shows a "Search the catalog" prompt (no API call fired). Submitting a search that returns zero results shows "No books found" (not an error, not blank).
result: pass

### 7. Student Catalog Pagination
expected: When a search returns more than one page of results, Previous/Next buttons appear. Clicking Next loads the next page without a full-page reload; the URL updates with the new page parameter so back/forward navigation restores the results.
result: skipped
reason: Not enough books in the catalog to trigger multi-page results

### 8. Librarian Book List — DataTable with Sorting
expected: /librarian/books shows a table with columns: Title, Author, ISBN, Available, Copies, and Actions. Clicking a column header sorts the rows (chevron icon shows sort direction). An empty state message shows when no books exist. The "Add Book" button appears in the header row.
result: pass

### 9. Librarian Add Book via ISBN Fetch
expected: On /librarian/books/new, entering an ISBN and clicking "Fetch Details" auto-fills the Title, Author, and Description fields (and cover URL internally). The fields become editable so the librarian can adjust them. Clicking "Save Book" saves the book and returns to the book list.
result: pass
note: Open Library unreachable from Docker container — "Service unavailable" fallback shown. Fallback behavior (form stays editable, manual entry possible) is correct per spec. Happy-path ISBN fetch not testable in this environment.

### 10. Librarian Add Book Manually (No ISBN)
expected: On /librarian/books/new, leaving ISBN blank and filling Title + Author manually, then clicking "Save Book" creates the book and navigates to the book list. A blank required field (Title or Author missing) shows an inline error without submitting.
result: pass

### 11. Librarian Edit Book
expected: From the librarian book list or book detail page, clicking Edit shows an inline form pre-filled with the book's current values. Changing a field and clicking "Save Changes" updates the book. Clicking "Discard Changes" cancels without saving.
result: pass

### 12. Librarian Delete Book (Soft Delete with Confirmation)
expected: Clicking Delete on a book opens a ConfirmDialog (not a browser alert). Confirming removes the book from the list (soft-delete — loan history preserved server-side). Cancelling with "Keep Book" closes the dialog without deleting.
result: pass

### 13. Librarian Add Physical Copy
expected: On the book detail page (/librarian/books/:id), the Physical Copies section has an "Add Copy" form. Entering an optional barcode and selecting condition, then submitting, adds the copy to the list with its CopyStatusBadge showing "available". The available_count in the book header increments.
result: pass

### 14. Librarian Mark Copy as Lost (Confirmation)
expected: On the book detail page, clicking "Mark as Lost" on a copy opens a ConfirmDialog. Confirming changes the copy's badge to red "lost" and decrements the available_count. Copy stays visible in the list. Cancelling closes the dialog without changes.
result: pass
note: Re-tested after fix (commit f7078e3) — removed deleted_at assignment from mark_copy_lost so copy remains visible with red "lost" badge.

### 15. Availability Badge Accuracy
expected: After adding a copy to a book (status: available), the AvailabilityBadge on the student catalog search results and on the book detail header reflects the correct count in real time (after next query). No stale counts visible after status changes.
result: pass

## Summary

total: 15
passed: 14
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

[none — all issues resolved]

## Resolved Issues

- test: 14
  truth: "Copy remains visible with red 'lost' badge after marking as lost"
  fix: "Removed copy.deleted_at assignment from mark_copy_lost (commit f7078e3)"
  verified: 2026-06-09

- test: 2
  truth: "NavBar and authenticated shell renders on all post-login pages"
  fix: "Removed invalid @import 'shadcn/tailwind.css' (commit ad55891); fixed post-login redirect to /catalog (commit 03b5299)"
  verified: 2026-06-09
