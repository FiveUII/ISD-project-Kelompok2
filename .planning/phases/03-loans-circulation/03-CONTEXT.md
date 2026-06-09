# Phase 3: Loans & Circulation - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers the full circulation workflow: librarians can check out a specific physical copy to a student (creating an active loan with a due date), and process returns (updating the copy back to available). Loans past their due date are automatically flagged as overdue — computed at query time, no background job. Students see all their active loans; librarians see all active loans and a filtered overdue view, both from a single loans dashboard.

This phase does NOT deliver fines, fine payment, email notifications, or scheduled jobs — those are Phase 4. Loan history (past returns) for students is a v2 deferred requirement.

</domain>

<decisions>
## Implementation Decisions

### Overdue Detection (Claude's Discretion)
- **D-01:** Overdue is computed at query time — `due_date < now() AND returned_at IS NULL`. It is a derived state, NOT a stored status column. No background job or APScheduler needed in Phase 3. The `status` field on a Loan (if any) should not include "overdue" — overdue is always calculated fresh from the timestamps. Phase 4's APScheduler handles scheduled email reminders; Phase 3 has no scheduler dependency.

### Checkout Flow
- **D-02:** Entry point is the **book detail page** (`/librarian/books/:id`). The existing Copies section (from Phase 2) shows each copy's status; librarian clicks "Check Out" on a specific copy with `status = available`. A modal opens for student selection.
- **D-03:** Student selection in the checkout modal uses **search-as-you-type** — librarian types a name or email, sees matching student results in a dropdown, selects one, and confirms the checkout.
- **D-04:** Due date is **always auto-calculated** — `today + loan_period_days` read from `library_settings`. It is shown in the confirmation but NOT editable by the librarian during checkout.
- **D-05:** Checkout validation is **API-level only**. Backend rejects: checking out a copy that is not available (status != 'available'), checking out to a non-existent student, or checking out to a non-student role. Frontend disables the "Check Out" button on copies that are not available — no complex pre-check needed.

### Loan Dashboards (Librarian)
- **D-06:** Single route `/librarian/loans` with two tabs: **"Active Loans"** and **"Overdue Loans"**. Uses the shadcn/ui DataTable pattern from Phase 2. One nav link ("Loans") for librarians.
- **D-07:** Loans table columns: Student name/email | Book title | Copy (barcode if set, else "Copy #id") | Due date | Status badge (Active / Overdue). Row-level action: **Return** button.
- **D-08:** Return action is available **from the loans dashboard only** (row-level Return button in the Active Loans tab). No return action on the book detail page.
- **D-09:** After a return is processed, the row **disappears immediately** — TanStack Query invalidates and refetches, and the returned loan drops from the active list. No animation or "Returned" in-place update.

### Student My Loans
- **D-10:** Students see **active loans only** — books currently checked out, not yet returned. Loan history (past returns) is a v2 deferred requirement (explicitly listed in REQUIREMENTS.md v2 section).
- **D-11:** Per-loan card shows: **Book title + author, Due date** (formatted as a readable date), and an **"Overdue" status badge** when past due. No copy barcode — not meaningful to students.
- **D-12:** Layout is a **card list** — each loan is a card, consistent with the student-facing BookSearchCard style from Phase 2. Route: `/my-loans`.
- **D-13:** Empty state message: "No active loans. Browse the catalog to find a book." with a link to `/catalog`. Consistent with Phase 2 empty-state patterns.

### Navigation
- **D-14:** Nav shell extension from Phase 2 (D-10 of 02-CONTEXT.md): students get a **"My Loans"** link pointing to `/my-loans`; librarians get a **"Loans"** link pointing to `/librarian/loans`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, tech stack constraints, out-of-scope boundaries
- `.planning/REQUIREMENTS.md` — LOAN-01 through LOAN-06 are the Phase 3 requirements; v2 deferred section confirms loan history is out of scope

### Roadmap
- `.planning/ROADMAP.md` §Phase 3 — Goal, success criteria (4 items), requirement list

### Prior Phase Context (required reading — patterns established here)
- `.planning/phases/01-foundation-auth/01-CONTEXT.md` — Auth model, Docker setup, RBAC DI pattern, JWT decisions
- `.planning/phases/02-catalog/02-CONTEXT.md` — Nav shell design (D-10), DataTable pattern (D-09), shadcn/ui usage, routing conventions, SQLAlchemy correlated subquery pattern

### Existing Models
- `backend/app/models/copy.py` — Copy model (status enum: available/on_loan/lost/withdrawn); checkout must set status → on_loan; return must set status → available
- `backend/app/models/library_settings.py` — `loan_period_days` field; due date calculation reads from this table (never hardcoded)
- `backend/app/core/enums.py` — `CopyStatus` enum — use these values exactly

### Existing Backend Patterns
- `backend/app/dependencies.py` — `require_librarian` and `get_current_user` DI — apply at router level for all `/librarian/loans` routes
- `backend/app/routers/books.py` — Router pattern to follow for new loans router
- `backend/app/core/db.py` — `get_db` AsyncSession dependency

### Existing Frontend Patterns
- `frontend/src/components/AppLayout.tsx` — Nav shell to extend with "My Loans" (student) and "Loans" (librarian) links
- `frontend/src/components/BookDataTable.tsx` — DataTable pattern to reuse for librarian loans table
- `frontend/src/components/BookSearchCard.tsx` — Card component to reuse/reference for student loan cards
- `frontend/src/App.tsx` — React Router setup to extend with `/my-loans` and `/librarian/loans` routes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/dependencies.py` — `require_librarian`, `get_current_user` DI functions. Use at router level for all librarian loan endpoints.
- `backend/app/core/enums.py` — `CopyStatus` enum. Checkout sets copy to `on_loan`; return sets copy back to `available`.
- `frontend/src/components/BookDataTable.tsx` — shadcn/ui DataTable — reuse directly for the librarian loans table. Columns and row actions follow the same pattern.
- `frontend/src/components/BookSearchCard.tsx` — Card component — use as reference style for student loan cards.
- `frontend/src/components/AppLayout.tsx` — Nav shell with role-aware links. Add "My Loans" for student, "Loans" for librarian.
- `frontend/src/components/CopyStatusBadge.tsx` — Status badge component — adapt or reference for the loan status badge (Active / Overdue).
- `frontend/src/components/ConfirmDialog.tsx` — Confirm dialog — reuse for the Return confirmation and checkout confirmation modal.

### Established Patterns
- **Router-level RBAC:** `router = APIRouter(prefix="/librarian/loans", dependencies=[Depends(require_librarian)])` for all librarian loan endpoints.
- **SQLAlchemy async:** All DB operations use `AsyncSession` + `await session.execute(select(...))`. Checkout and return are write operations — use `session.add()` / `await session.commit()`.
- **Pydantic v2 schemas:** New loan schemas go in `backend/app/schemas/loans.py`.
- **TanStack Query v5:** `useMutation` for checkout and return actions; `useQuery` for loan list. Invalidate the loans query key on mutation success to trigger a refetch and remove the returned row.
- **Alembic migrations:** New `Loan` table requires a new Alembic migration file.

### Integration Points
- `backend/app/main.py` — Register new loans router here (follow `books.router` include pattern).
- `frontend/src/App.tsx` — Add `/my-loans` (student-protected) and `/librarian/loans` (librarian-protected) routes inside the shared layout shell.
- `backend/app/models/__init__.py` — Import new Loan model for Alembic autogenerate to detect it.
- Book detail page (`frontend/src/pages/BookDetailPage.tsx`) — Add "Check Out" button to available copy rows in the Copies section.

</code_context>

<specifics>
## Specific Ideas

- Checkout modal on book detail: a shadcn/ui Dialog with a search input for student lookup. Student results appear as a dropdown list. Shows the computed due date before confirming.
- Student loan cards: similar visual to BookSearchCard — book title prominent, due date in a muted/secondary style, red "Overdue" badge when past due.
- Librarian loans table: "Overdue Loans" tab filters the same data server-side (or client-side) — whichever is simpler given pagination constraints.

</specifics>

<deferred>
## Deferred Ideas

- **Loan history for students** (past returns) — explicitly v2 in REQUIREMENTS.md. Out of scope for Phase 3.
- **Librarian due-date override** during checkout — not needed; all loans use the standard loan period.
- **Checkout from loans dashboard** (alternate entry point) — entry point is book detail page only in Phase 3.
- **Return from book detail page** — return is from loans dashboard only in Phase 3.
- **Student outstanding fine balance on My Loans page** — Phase 4 (fines not in scope yet).

</deferred>

---

*Phase: 3-Loans & Circulation*
*Context gathered: 2026-06-09*
