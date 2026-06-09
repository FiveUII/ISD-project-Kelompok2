# Phase 2: Catalog - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 2-Catalog
**Areas discussed:** ISBN auto-fetch behavior, Search approach, Catalog UI layout & routing, Availability display

---

## ISBN Auto-Fetch Behavior

**Question 1: When Open Library returns no result**

| Option | Description | Selected |
|--------|-------------|----------|
| Show error, stay on form | Display inline error; librarian fills all fields manually | ✓ |
| Fall through to manual entry | ISBN stays pre-filled, no error message | |
| Show what was found, fill the rest | Pre-fill partial data, leave blanks editable | |

**User's choice:** Show error, stay on form
**Notes:** Simplest, no partial state to manage.

---

**Question 2: When Open Library is unreachable**

| Option | Description | Selected |
|--------|-------------|----------|
| Show 'Service unavailable, fill manually' | Inline error consistent with not-found handling | ✓ |
| Retry once then show error | One automatic retry with short timeout, then error | |
| You decide | Claude picks simplest approach | |

**User's choice:** Show 'Service unavailable, fill manually'
**Notes:** Consistent error handling regardless of failure mode.

---

**Question 3: What fields to auto-fill on success**

| Option | Description | Selected |
|--------|-------------|----------|
| Title, author, description | Only the three fields scoped in CATL-02 | ✓ |
| All available fields | Fill title, author, description, publisher, publish_year, cover_url | |
| You decide | Claude fills whatever Open Library reliably returns | |

**User's choice:** Title, author, description only
**Notes:** Stays within CATL-02 scope. Publisher/publish_year in the model but not auto-filled.

---

## Search Approach

**Question 1: Match strategy**

| Option | Description | Selected |
|--------|-------------|----------|
| Exact ILIKE substring | PostgreSQL ILIKE, no extensions needed | ✓ |
| Trigram fuzzy (pg_trgm) | Tolerates typos, requires pg_trgm extension | |
| You decide | Claude picks based on scale and complexity | |

**User's choice:** Exact ILIKE substring
**Notes:** Sufficient for school library scale (<10k books). No pg_trgm overhead.

---

**Question 2: Field targeting**

| Option | Description | Selected |
|--------|-------------|----------|
| Single query checks all three | One ?q= param checks title OR author OR ISBN | ✓ |
| Field-specific with dropdown | Dropdown to select which field, then one text box | |

**User's choice:** Single query checks all three
**Notes:** Simpler UX, matches CATS-01 scope.

---

**Question 3: Pagination**

| Option | Description | Selected |
|--------|-------------|----------|
| Offset pagination, 20 results per page | Standard page controls (?page=&page_size=) | ✓ |
| Load more / infinite scroll | Single button loads 20 more | |
| You decide | Claude picks simplest approach for school catalog | |

**User's choice:** Offset pagination, 20 results per page
**Notes:** Consistent with FastAPI query params pattern. Simple to implement.

---

## Catalog UI Layout & Routing

**Question 1: Student vs. librarian pages**

| Option | Description | Selected |
|--------|-------------|----------|
| Separate routes | /catalog for students, /librarian/books for management | ✓ |
| Same page, role-gated controls | One /books route, conditional rendering per role | |
| You decide | Claude picks based on RBAC approach | |

**User's choice:** Separate routes
**Notes:** Cleaner RBAC, separate concerns, easier to test.

---

**Question 2: Copy management location**

| Option | Description | Selected |
|--------|-------------|----------|
| Inline on book detail page | Copies section on /librarian/books/:id | ✓ |
| Separate /copies route | Dedicated copies page per book | |
| You decide | Claude picks to minimize navigation steps | |

**User's choice:** Inline on book detail page
**Notes:** Fewer navigation steps for librarians; copies are always accessed in book context.

---

**Question 3: Librarian book list layout**

| Option | Description | Selected |
|--------|-------------|----------|
| Data table (shadcn/ui DataTable) | Sortable columns, row actions, data-dense | ✓ |
| Card grid | Visual cards with cover/title/author | |
| You decide | Claude picks for librarian management interface | |

**User's choice:** Data table
**Notes:** Data-dense, appropriate for catalog management. shadcn/ui DataTable already in stack.

---

**Question 4: Shared navigation layout**

| Option | Description | Selected |
|--------|-------------|----------|
| Introduce a shared layout shell | Root layout with navbar, auth pages outside the shell | ✓ |
| Standalone pages only | No shared nav in Phase 2, add in later phase | |
| You decide | Claude picks to reduce rework across phases | |

**User's choice:** Introduce a shared layout shell
**Notes:** Sets the pattern for Phases 3 & 4. Auth pages remain outside shell.

---

## Availability Display

**Question 1: What students see**

| Option | Description | Selected |
|--------|-------------|----------|
| Available copies count only | e.g. "3 available" — answers "can I borrow this?" | ✓ |
| Available out of total copies | e.g. "3 of 5 available" — exposes total holdings | |
| You decide | Claude picks based on core value | |

**User's choice:** Available copies count only
**Notes:** Aligns exactly with CATS-02. Total copies is internal data.

---

**Question 2: How availability is fetched**

| Option | Description | Selected |
|--------|-------------|----------|
| Included in book list response | Subquery/join in the API response — single request | ✓ |
| Separate call per book | Second API call per book for counts | |
| You decide | Claude picks to avoid N+1 queries | |

**User's choice:** Included in book list response
**Notes:** Prevents N+1 queries. Standard SQLAlchemy subquery pattern.

---

**Question 3: Soft-deleted books visibility**

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from all results | deleted_at IS NULL filter universal | ✓ |
| Show in librarian view only | Role-based filter; students never see deleted | |
| You decide | Claude picks based on soft-delete purpose | |

**User's choice:** Exclude soft-deleted books from all results
**Notes:** Soft-delete preserves loan history, not to enable recovery/visibility. Simpler filtering.

---

## Claude's Discretion

- **Open Library timeout:** 5-second HTTPX timeout; on timeout, treat as unreachable (D-02 error path)
- **Student catalog access:** `/catalog` requires authentication; unauthenticated users redirect to `/login`
- **Librarian access to /catalog:** Librarians can also use `/catalog` for search; `/librarian/books` is the management view
- **Copy detail in librarian view:** Show barcode and status for each copy; soft-deleted copies (deleted_at set) are hidden

## Deferred Ideas

None — discussion stayed within phase scope.
