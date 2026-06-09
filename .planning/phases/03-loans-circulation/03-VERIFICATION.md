---
phase: 03-loans-circulation
status: human_needed
verified: 2026-06-09
must_haves_total: 4
must_haves_verified: 4
automated_checks: passed
human_verification:
  - "Complete checkout → return → overdue detection cycle in running Docker stack"
---

# Phase 03: Loans & Circulation — Verification Report

**Phase goal:** Librarians can process checkouts and returns; overdue loans are flagged automatically; both roles have dashboard visibility over all active and overdue loans.

**Requirements:** LOAN-01, LOAN-02, LOAN-03, LOAN-04, LOAN-05, LOAN-06

---

## Automated Verification: PASSED

### Must-Have Checks

**LOAN-01 — Librarian can check out a copy to a student**
- `backend/app/routers/loans.py` → `POST /api/librarian/loans/checkout` exists ✓
- Validates copy availability (409 if not available) ✓
- Validates student role (400 if not student) ✓
- Creates Loan record, sets copy.status = on_loan ✓
- Returns LoanResponse with is_overdue computed ✓
- Protected by `require_librarian` at router level ✓

**LOAN-02 — Librarian can process a return**
- `backend/app/routers/loans.py` → `PATCH /api/librarian/loans/{loan_id}/return` exists ✓
- Sets loan.returned_at = now(), copy.status = available ✓
- 409 idempotency check for already-returned loans ✓
- Protected by `require_librarian` at router level ✓

**LOAN-03 — Overdue flagged automatically**
- `backend/app/schemas/loans.py` → `is_overdue` computed field: `due_date < now(UTC) and returned_at is None` ✓
- No stored status column; computed at query time (D-01) ✓
- `GET /api/librarian/loans?overdue=true` filters `Loan.due_date < now` ✓
- Frontend: LibrarianLoansPage "Overdue Loans" tab passes `overdue=true` ✓
- Frontend: MyLoansPage shows red Overdue badge when `loan.is_overdue === true` ✓

**LOAN-04 — Student can view active loans**
- `frontend/src/pages/MyLoansPage.tsx` exists ✓
- `GET /api/loans/my` endpoint in student_loans_router, authenticated ✓
- user_id from JWT sub only — never from client (T-03-01 compliant) ✓
- Returns only non-returned loans (`returned_at IS NULL`) ✓
- App.tsx `/my-loans` route in authenticated AppLayout (non-requireLibrarian) ✓

**LOAN-05 — Librarian can view all active loans**
- `GET /api/librarian/loans` (overdue=false) lists all active loans ✓
- LibrarianLoansPage "Active Loans" tab displays them with Student, Book, Copy, Due Date, Status, Return columns ✓

**LOAN-06 — Librarian can view overdue loans**
- `GET /api/librarian/loans?overdue=true` filters by due_date < now ✓
- LibrarianLoansPage "Overdue Loans" tab queries with overdue=true ✓

### Build and Compile Checks
- `npx tsc --noEmit` — PASSED ✓
- `npm run build` — PASSED (455KB bundle, 4.64s) ✓
- `python -m pytest tests/ -q` — 101 passed, 1 warning (pydantic field shadow — non-functional) ✓
- `python -m py_compile backend/app/routers/loans.py backend/app/schemas/loans.py backend/app/models/loan.py` — PASSED ✓

### Key File Existence
- `frontend/src/pages/MyLoansPage.tsx` ✓
- `frontend/src/api/loans.ts` (getMyLoans, getLibrarianLoans, returnLoan, checkoutCopy, searchStudents) ✓
- `frontend/src/pages/LibrarianLoansPage.tsx` ✓
- `backend/app/routers/loans.py` ✓
- `backend/app/models/loan.py` ✓
- `backend/alembic/versions/0005_loans_table.py` ✓

---

## Human Verification Required

All automated checks pass. The following items require testing in the running Docker Compose stack:

### 1. Checkout Flow
Start stack: `docker compose up`

- Log in as librarian
- Navigate to /librarian/books → click a book → go to Book Detail
- Find a copy with status "available" — verify "Check Out" button appears
- Click "Check Out" → verify modal opens with student search input
- Type part of a student email → verify matching students appear in dropdown
- Select a student → verify their name/email shows as selected and due date is displayed (read-only)
- Click "Confirm Checkout" → verify modal closes, copy status changes from "Available" to "On Loan"

### 2. Librarian Loans Dashboard
- Navigate to /librarian/loans (Loans link in nav)
- Verify "Active Loans" tab is selected by default
- Verify the checked-out loan appears with correct columns: student, book title, copy, due date, Active status badge, Return button
- Click "Overdue Loans" tab → verify only past-due loans appear (may be empty if no overdue loans exist)

### 3. Return Flow
- In Active Loans tab, click Return button on the loan just created
- Verify ConfirmDialog appears asking to confirm return
- Click confirm → verify row disappears immediately from the table
- Navigate back to Book Detail → verify copy status is back to "Available"

### 4. Student My Loans
- Log out, log in as the student used for checkout
- Navigate to /my-loans (My Loans link in nav)
- Verify the active loan card appears with book title, due date, and no Overdue badge (loan is current)
- Verify the loan disappears after it was returned (refresh if needed)
- Verify empty state shows "No active loans. Browse the catalog to find a book."

### 5. Overdue Detection
```sql
docker compose exec db psql -U postgres -d librarydb -c "UPDATE loans SET due_date = NOW() - INTERVAL '1 day' WHERE returned_at IS NULL LIMIT 1;"
```
- Reload /my-loans → verify red "Overdue" badge appears on that loan
- Reload /librarian/loans "Overdue Loans" tab → verify that loan appears

---

## Code Review Results

`03-REVIEW.md` written. No critical issues found. 3 warnings:
- WR-01: `is_overdue` guard comment missing (correctness documentation)
- WR-02: Student search backend has no minimum-length guard (minor info disclosure within admin boundary)
- WR-03: `returnMutation` in LibrarianLoansPage has no `onError` handler (silent failure UX)

---

## Next Steps

Run human verification above, then:

```
/gsd-verify-work 3
```

Verify-work will walk through each UAT item and mark the phase complete when all tests pass.
