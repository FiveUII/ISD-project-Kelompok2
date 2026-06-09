# Library Management System

## What This Is

A web-based Library Management System for a school or university that replaces manual/paper-based tracking. Students can search the book catalog and see availability; librarians manage the catalog, process borrowing and returns, and track overdue fines. The system sends email reminders for due dates and overdue books.

## Core Value

Students can find any book and know if it's available; librarians can process a borrow or return in seconds — no paper required.

## Requirements

### Validated

- ✓ Student and librarian accounts with role-based access — Phase 1 (API) + Phase 2 (UI route guards, RBAC on all catalog endpoints)
- ✓ Students can search the book catalog by title, author, or ISBN — Phase 2
- ✓ Students can see real-time book availability — Phase 2 (correlated subquery, AvailabilityBadge)
- ✓ Librarians can add books manually or via ISBN auto-fetch — Phase 2 (AddBookPage, ISBNFetchButton, Open Library service)

### Active

- [ ] Librarians can check out books to students
- [ ] Librarians can process book returns
- [ ] System tracks due dates for all active loans
- [ ] System tracks and calculates overdue fines
- [ ] Students receive email reminders before due date
- [ ] Students receive email alerts when overdue
- [ ] Librarians can view all active loans and overdue items
- [ ] System runs fully in Docker (containerized deployment)

### Out of Scope

- Mobile app — web-only for v1
- E-books / digital content — physical books only
- Integration with external library systems — standalone for v1
- Self-service kiosk / RFID — manual librarian processing only

## Context

- Replacing a paper/spreadsheet-based tracking process
- School/university context: two user roles — students (read/borrow) and librarians (full management)
- ISBN lookup via a public API (e.g., Open Library) to auto-populate book details
- Email notifications for due-date reminders and overdue alerts

## Constraints

- **Tech Stack**: FastAPI (Python) + React + PostgreSQL — team knows this stack
- **Deployment**: Must run in Docker (docker-compose for local + production)
- **Platform**: Web only — no mobile app in v1
- **Auth**: Role-based — student vs librarian permissions enforced at API level

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Django/Flask | Async support, auto-generated docs, fast development | — Pending |
| PostgreSQL over SQLite | Concurrent access, production-grade reliability needed | — Pending |
| Docker-first deployment | Reproducible environment, easy onboarding | — Pending |
| ISBN auto-fetch via Open Library API | Free, no API key needed, good coverage | Working; unreachable from Docker in test env — fallback manual entry acceptable for v1 |
| SQLAlchemy correlated subquery for available_count | Avoids N+1; single SQL statement for list + detail | Confirmed working — Phase 2 |
| mark_copy_lost: status-only update, no deleted_at | Copy must stay visible with red badge after marking lost | Validated via UAT — Phase 2 |
| ISBN endpoint registered before /{book_id} route | FastAPI path precedence — /isbn-fetch would match /{book_id} | Confirmed working — Phase 2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-09 after Phase 2*
