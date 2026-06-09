---
phase: 02
slug: catalog
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-09
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Browser → FastAPI | HTTPS (proxied via Nginx) | JWT tokens, book/copy data, ISBN values |
| FastAPI → Open Library API | HTTPS | ISBN strings, book metadata (public data) |
| FastAPI → PostgreSQL | Internal Docker network | Book records, copy status, user roles |
| AppLayout → Page components | React component tree | JWT token, user role (from Zustand store) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | Broken Access Control | AppLayout route structure | accept | Auth pages (login, register, verify-email, forgot-password, reset-password) remain outside AppLayout wrapper per App.tsx route structure | closed |
| T-01-02 | Broken Access Control | AppLayout auth guard | accept | `!token → <Navigate to="/login" replace />` in AppLayout.tsx using `useAuthStore` | closed |
| T-01-03 | Broken Access Control | AppLayout role guard | accept | `requireLibrarian && user?.role !== "librarian" → <Navigate to="/catalog" replace />` — students cannot reach `/librarian/*` | closed |
| T-02-01 | SSRF | `isbn_service.py` | accept | `_validate_isbn()` regex `^[a-zA-Z0-9-]{8,17}$` applied before any HTTPX call; author and works path keys validated against `AUTHOR_KEY_RE`/`WORK_KEY_RE` patterns (fixed CR-02) | closed |
| T-02-02 | Broken Access Control | `books.py` routers | accept | `librarian_router` and `copies_router` both declare `dependencies=[Depends(require_librarian)]` at router level — no inline per-route checks | closed |
| T-02-03 | Information Disclosure | All book/copy queries | accept | Every SELECT in `books.py` includes `Book.deleted_at.is_(None)` and `Copy.deleted_at.is_(None)` — soft-deleted records never returned | closed |
| T-03-01 | Broken Access Control | Page components | accept | No inline role checks in any page component — AppLayout shell owns all route guards; pages only render | closed |
| T-03-02 | Data Integrity | Frontend availability display | accept | `available_count` sourced exclusively from API correlated subquery — no client-side recalculation from copies array | closed |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-01-01 | Auth route structure verified by code inspection — AppLayout wrapper is applied only to `/catalog` and `/librarian/*` routes in App.tsx | user (session 2026-06-09) | 2026-06-09 |
| AR-02-02 | T-01-02 | Auth guard logic is simple token-presence check; JWT validation happens at API layer | user (session 2026-06-09) | 2026-06-09 |
| AR-02-03 | T-01-03 | Role guard redirect to `/catalog` confirmed in AppLayout.tsx source | user (session 2026-06-09) | 2026-06-09 |
| AR-02-04 | T-02-01 | SSRF mitigations applied — ISBN input validation + key path regex guards added in CR-02 fix commit | user (session 2026-06-09) | 2026-06-09 |
| AR-02-05 | T-02-02 | RBAC at router level confirmed in books.py — router-level dependencies pattern used throughout | user (session 2026-06-09) | 2026-06-09 |
| AR-02-06 | T-02-03 | `deleted_at.is_(None)` filter confirmed present on all queries by verifier (13/13 must-haves) | user (session 2026-06-09) | 2026-06-09 |
| AR-02-07 | T-03-01 | Page components contain no `user.role` conditional renders for access control — confirmed by code review | user (session 2026-06-09) | 2026-06-09 |
| AR-02-08 | T-03-02 | Frontend reads `available_count` from API response exclusively — no copies array arithmetic | user (session 2026-06-09) | 2026-06-09 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-09 | 8 | 8 | 0 | user-accepted (session 2026-06-09) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-09
