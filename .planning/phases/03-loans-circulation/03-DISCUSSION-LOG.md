# Phase 3: Loans & Circulation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-09
**Phase:** 3-Loans & Circulation
**Areas discussed:** Checkout flow, Loan dashboards, Student My Loans

---

## Checkout Flow

**Q1: Entry point for checkout**

| Option | Description | Selected |
|--------|-------------|----------|
| Book detail page | Librarian finds the book, goes to /librarian/books/:id, clicks "Check Out" on a specific available copy. Modal opens for student selection. | ✓ |
| Dedicated checkout form | Librarian goes to /librarian/loans/new, searches for student + book, system selects available copy. | |
| Both entry points | From book detail AND from a 'New Checkout' button on the loans dashboard. | |

**User's choice:** Book detail page
**Notes:** Reuses existing book detail page — minimal new routing.

---

**Q2: Student lookup method in checkout modal**

| Option | Description | Selected |
|--------|-------------|----------|
| Search-as-you-type | Text input, librarian types name or email, sees matching results in dropdown, selects. | ✓ |
| Student ID / email exact entry | Librarian types exact email or student ID. No dropdown. | |
| Dropdown of all students | Select input listing all students. | |

**User's choice:** Search-as-you-type
**Notes:** Fast and practical for real-world use.

---

**Q3: Due date during checkout**

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-calculated, not editable | Due date = today + loan_period_days from library_settings. Shown in confirmation, not editable. | ✓ |
| Auto-calculated but overridable | Default to loan_period_days but librarian can edit the date field. | |

**User's choice:** Always auto-calculated, no override
**Notes:** Keeps checkout fast and consistent. Special-case loan periods deferred.

---

**Q4: Checkout validation**

| Option | Description | Selected |
|--------|-------------|----------|
| API-level only | Backend rejects invalid states. Frontend disables button on non-available copies. | ✓ |
| API-level + frontend pre-check | Frontend also checks if student has outstanding overdue loans before allowing checkout. | |
| You decide | Claude picks validation approach. | |

**User's choice:** API-level validation only
**Notes:** Pre-checking overdue status as a block is out of scope for Phase 3 (no fine/overdue policy defined yet).

---

## Loan Dashboards

**Q1: Librarian loans page structure**

| Option | Description | Selected |
|--------|-------------|----------|
| Single page with tabs | /librarian/loans with "Active Loans" and "Overdue Loans" tabs. DataTable pattern. | ✓ |
| Separate routes | Two pages: /librarian/loans and /librarian/loans/overdue. | |

**User's choice:** Single page with tabs
**Notes:** One nav link, consistent with Phase 2 DataTable pattern.

---

**Q2: Loans table columns**

| Option | Description | Selected |
|--------|-------------|----------|
| Student, Book, Copy barcode, Due date, Status | Full columns with barcode. Row action: Return. | ✓ |
| Student, Book, Due date, Status (no barcode) | Simpler, no barcode. | |
| You decide | Claude picks columns. | |

**User's choice:** Student, Book, Copy barcode, Due date, Status (Recommended)
**Notes:** Copy barcode helps librarians identify physical items. Falls back to "Copy #id" if no barcode set.

---

**Q3: Return entry point**

| Option | Description | Selected |
|--------|-------------|----------|
| Loans dashboard only | Row-level Return button in active loans table. | ✓ |
| Both: loans dashboard + book detail | Return from both locations. | |
| Book detail page only | Return from copy row on book detail page. | |

**User's choice:** Loans dashboard only
**Notes:** Centralizes circulation management. Book detail page is for catalog management.

---

**Q4: Post-return UX**

| Option | Description | Selected |
|--------|-------------|----------|
| Row disappears, table refreshes | Returned loan drops from active list immediately via TanStack Query invalidation. | ✓ |
| Row stays with 'Returned' status, then fades | Brief confirmation before disappearing. | |
| You decide | Claude handles post-return UX. | |

**User's choice:** Row disappears, table refreshes
**Notes:** Standard TanStack Query mutation → invalidateQueries → refetch pattern.

---

## Student My Loans

**Q1: Content scope**

| Option | Description | Selected |
|--------|-------------|----------|
| Active loans only | Only currently checked-out books (not returned). Matches LOAN-04. | ✓ |
| Active + loan history | Current loans and past returns. Goes beyond LOAN-04 (v2 deferred). | |

**User's choice:** Active loans only
**Notes:** Loan history is explicitly v2 deferred in REQUIREMENTS.md.

---

**Q2: Per-loan information**

| Option | Description | Selected |
|--------|-------------|----------|
| Book title, Due date, Overdue badge | Book title + author, due date, Overdue badge if past due. | ✓ |
| Book title, Due date, Overdue badge + days overdue | Same plus "X days overdue" text. | |
| Book title, Copy barcode, Due date, Overdue badge | Includes copy barcode — not meaningful to students. | |

**User's choice:** Book title, Due date, Overdue badge
**Notes:** Clean and actionable — tells the student exactly what they need.

---

**Q3: Layout**

| Option | Description | Selected |
|--------|-------------|----------|
| Card list | Each loan is a card, consistent with BookSearchCard student-facing style. | ✓ |
| DataTable | Admin-style table — more dense, less appropriate for students. | |
| You decide | Claude picks layout. | |

**User's choice:** Card list
**Notes:** Consistent with the student-facing catalog design from Phase 2.

---

**Q4: Empty state**

| Option | Description | Selected |
|--------|-------------|----------|
| Empty state with link to Catalog | "No active loans. Browse the catalog to find a book." + /catalog link. | ✓ |
| Plain 'No active loans' message | Text only, no action. | |
| You decide | Claude handles empty state. | |

**User's choice:** Empty state with a link to Catalog
**Notes:** Guides the student. Consistent with Phase 2 empty-state patterns.

---

## Claude's Discretion

- **Overdue detection mechanism:** Computed at query time (`due_date < now() AND returned_at IS NULL`). No stored overdue status, no background job in Phase 3. User skipped this gray area — handled by Claude.
- **Loan model schema:** New `Loan` table with `id`, `copy_id` (FK→copies), `user_id` (FK→users), `checked_out_at`, `due_date`, `returned_at` (nullable). Overdue = derived from timestamps.
- **Alembic migration:** New migration for the Loan table.
- **Student search API endpoint:** New endpoint for the checkout modal's search-as-you-type. Returns student name + email + id for matching results.

## Deferred Ideas

- Loan history for students (past returns) — v2 deferred per REQUIREMENTS.md
- Librarian due-date override during checkout — not needed
- Checkout from loans dashboard (alternate entry point) — not in Phase 3
- Return from book detail page — not in Phase 3
- Student outstanding fine balance on My Loans page — Phase 4
