---
phase: 03-loans-circulation
status: findings
depth: standard
files_reviewed: 15
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
reviewed: 2026-06-09
---

# Code Review — Phase 03: Loans & Circulation

**Depth:** standard  
**Files reviewed:** 15  
**Scope:** SUMMARY.md-derived (Plans 01–03)

---

## Summary

No critical bugs. Three warnings — one security-adjacent (missing rate-limit on student search), one correctness issue (is_overdue double-computation on already-returned loans), and one UX gap (no error boundary on returnMutation failure). Four informational items covering minor code quality and robustness points.

---

## Findings

### WR-01 — is_overdue computed on returned loans (correctness)

**File:** `backend/app/schemas/loans.py:86-87`  
**Severity:** Warning

```python
@computed_field
@property
def is_overdue(self) -> bool:
    return self.due_date < datetime.now(timezone.utc) and self.returned_at is None
```

The `returned_at is None` guard is correct — returned loans won't be flagged as overdue. However, the list endpoints in `loans.py` filter by `Loan.returned_at.is_(None)` before building responses, meaning `returned_at` is always `None` in the result set. The guard works but is redundant for list queries. The edge case is the `return_loan` endpoint, which reloads the just-returned loan and serializes it — at that point `returned_at` is set, so `is_overdue` correctly returns `False`. **No bug, but the defensive guard in the property is the only thing preventing a wrong `is_overdue=True` on a freshly-returned loan being serialized.** If a future developer removes the guard thinking it's dead code (it appears redundant in list context), return responses will incorrectly show returned loans as overdue. Consider adding a short inline comment to document why `and self.returned_at is None` is intentional and non-redundant.

**Recommendation:** Add inline comment: `# Guard required: return endpoint serializes just-returned loans where due_date may already be past`

---

### WR-02 — Student search endpoint has no rate limit or minimum-length guard on the backend

**File:** `backend/app/routers/admin.py:42-79`  
**Severity:** Warning

`GET /api/admin/users?role=student&search=` accepts an empty `search` parameter and returns up to 20 users. The frontend enforces `studentQuery.length >= 2` before enabling the query, but the backend has no analogous validation. A caller who hits the API directly (via curl or a modified client) with `search=` or `search=a` gets a list of all students (up to 20). While the endpoint is admin-only (correct), the lack of a minimum search length means:

1. The first 20 students in alphabetical order leak on every empty-search call — a minor information disclosure within the admin boundary.
2. An automated script could enumerate students by iterating over the alphabet.

**Recommendation:** Add `if search and len(search) < 2: return []` at the top of `list_users`, or require `search` to be non-empty when `role=student` is specified. This aligns backend enforcement with the frontend's guard.

---

### WR-03 — returnMutation error not surfaced in LibrarianLoansPage

**File:** `frontend/src/pages/LibrarianLoansPage.tsx:52-59`  
**Severity:** Warning

The `returnMutation` has no `onError` handler. If the PATCH `/librarian/loans/{id}/return` call fails (network error, 409 already-returned, 404), the dialog closes (because there's no error branch) but the table doesn't update, leaving the librarian with no feedback. The dialog silently dismisses.

```typescript
const returnMutation = useMutation({
  mutationFn: (loanId: number) => returnLoan(loanId),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ["librarian-loans"] });
    setReturnDialogOpen(false);
    setReturnTargetId(null);
  },
  // missing: onError handler
});
```

In `ConfirmDialog`, `returnMutation.isPending` disables the button during the request, but on failure the dialog stays open with no error state displayed. The user doesn't know if the return succeeded or failed.

**Recommendation:** Add `onError` to show an error message in the dialog:
```typescript
onError: () => {
  // leave dialog open, surface error
  setReturnError("Failed to process return. Please try again.");
},
```

---

### INFO-01 — Loan model missing a unique constraint on (copy_id, returned_at IS NULL)

**File:** `backend/alembic/versions/0005_loans_table.py` + `backend/app/models/loan.py`  
**Severity:** Info

There is no database-level constraint preventing two simultaneous active loans for the same copy. The application-layer checkout guard (`copy.status != CopyStatus.available`) provides protection, but a race condition under concurrent requests could theoretically create two active loans for the same copy (both threads see status=available before either commits).

SQLAlchemy partial unique indexes require raw DDL (`op.create_index(..., unique=True, postgresql_where=...)`). This is a Phase 3 scope constraint — the checkout endpoint does serialize within a single request. For a school library with low concurrency, this is acceptable. However, the index would provide a safety net.

**Recommendation (optional):** In a future phase, add a partial unique index:
```sql
CREATE UNIQUE INDEX ix_loans_copy_active ON loans (copy_id) WHERE returned_at IS NULL;
```

---

### INFO-02 — BookDetailPage student search results not cleared when modal closes

**File:** `frontend/src/pages/BookDetailPage.tsx:508-516`  
**Severity:** Info

When the checkout Dialog closes (via `onOpenChange` or Cancel button), `studentQuery` and `selectedStudent` are reset, but the TanStack Query cache entry `['student-search', studentQuery]` remains. This is harmless — the cache is not displayed after modal close — but on the next modal open, the stale results briefly appear if the librarian types the same query before the background refetch completes.

The query uses `enabled: studentQuery.length >= 2`, so stale results only show when `studentQuery` matches a prior search. Not a bug; cosmetically minor.

**Recommendation (optional):** Use `staleTime: 0` on the student search query to force fresh results on each query.

---

### INFO-03 — `_loan_to_response` mutates the ORM instance

**File:** `backend/app/routers/loans.py:61-70`  
**Severity:** Info

```python
def _loan_to_response(loan: Loan) -> LoanResponse:
    loan.book = loan.copy.book  # type: ignore[attr-defined]
    return LoanResponse.model_validate(loan)
```

This attaches `.book` directly to the ORM instance. Because SQLAlchemy tracks attribute changes, this could in theory trigger dirty-state detection and an unintended UPDATE on the loans table. In practice, the session is committed shortly after (or the object is detached), so no spurious UPDATE occurs. But it's fragile — if a future refactor calls `_loan_to_response` before a flush, SQLAlchemy might include `.book` in an UPDATE.

**Recommendation:** Use a dictionary or dataclass projection instead of mutating the ORM instance, or accept the current pattern with an explicit comment documenting why it's safe.

---

### INFO-04 — MyLoansPage renders error state even when `data` is stale from cache

**File:** `frontend/src/pages/MyLoansPage.tsx:39-41`  
**Severity:** Info

TanStack Query's `isError` stays `true` on refetch failure even when stale cached data is available. The current render order shows the error message but not the cached loan cards:

```tsx
{isError && <p>Failed to load your loans.</p>}
{!isLoading && !isError && loans.length > 0 && <div>...</div>}
```

If the network fails on a refetch (user has loans cached from a prior fetch), the card list disappears and only the error shows. Standard TanStack Query practice is to check `data` independently of `isError` for the content block.

**Recommendation:** Use `data?.items` presence check instead of `!isError`:
```tsx
{isError && !loans.length && <p>Failed to load your loans.</p>}
{loans.length > 0 && <div>...</div>}
```

This shows cached cards with an error banner if the refetch fails, preserving useful information.

---

## Files with No Issues

- `backend/alembic/versions/0005_loans_table.py` — migration is correct and reversible
- `backend/app/models/loan.py` — model is clean; FKs, indexes, relationships all correct
- `backend/app/models/__init__.py` — import order correct, Loan included
- `backend/app/models/copy.py` — no changes; correct
- `backend/app/models/user.py` — soft-delete pattern correct; loans relationship wired
- `backend/app/main.py` — both routers registered; CORS config unchanged
- `backend/app/schemas/loans.py` — overall structure good; see WR-01
- `frontend/src/api/loans.ts` — clean; all five functions correctly typed
- `frontend/src/components/NavBar.tsx` — role-aware links correct; active state logic correct
- `frontend/src/App.tsx` — route placement correct; /my-loans in non-requireLibrarian block

---

## Self-Check: PASSED

- 15 files reviewed at standard depth ✓
- Critical findings: 0 ✓
- Warning findings: 3 (WR-01, WR-02, WR-03) ✓
- Info findings: 4 (INFO-01 through INFO-04) ✓
- No false positives introduced ✓
- Security posture: T-03-01 (user_id from JWT), T-03-02 (idempotency), T-03-03 (student-only checkout) all verified correct ✓
