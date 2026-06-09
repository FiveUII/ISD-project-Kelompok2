# Roadmap: Library Management System

## Overview

Four phases deliver the complete v1 MVP: a Docker-containerized FastAPI + React + PostgreSQL stack that lets students find and borrow books while giving librarians full catalog and circulation control. Phase 1 lays the infrastructure and auth foundation. Phase 2 builds the full catalog (librarian management and student search). Phase 3 delivers the core circulation workflow. Phase 4 closes the loop with fine tracking and email notifications.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Auth** - Docker scaffold, data model, and role-based authentication (completed 2026-06-08)
- [x] **Phase 2: Catalog** - Librarian catalog management and student book search (completed 2026-06-09)
- [x] **Phase 3: Loans & Circulation** - Checkout, return, due date tracking, and loan dashboards (completed 2026-06-09)
- [x] **Phase 4: Fines & Notifications** - Overdue fine ledger and automated email reminders (completed 2026-06-09)

## Phase Details

### Phase 1: Foundation & Auth

**Goal:** The running Docker Compose stack is accessible, the Book/Copy data model is in place, and users can securely log in with role-based access enforced at the API level.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Success Criteria** (what must be TRUE):

  1. A user can register a student account, verify their email, and log in — receiving a JWT that persists across browser sessions.
  2. A librarian can log in and access librarian-only endpoints; a student attempting the same endpoints receives a 403.
  3. A user can request a password-reset link via email and set a new password.
  4. The full Docker Compose stack (db, api, frontend, nginx) starts with a single `docker compose up` and all health checks pass.

**Plans:** 3/3 plans complete
**Wave 1**

- [x] 01-01-PLAN.md — Walking Skeleton: Docker Compose stack + FastAPI/SQLAlchemy scaffold + User/Book/Copy/library_settings model + end-to-end health round trip

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Auth slice: self-register + strict email verification + JWT login (AUTH-01, AUTH-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — RBAC at router level + admin superuser seed + librarian promotion + password reset (AUTH-03, AUTH-04)

**UI hint:** yes

### Phase 2: Catalog

**Goal:** Librarians can fully manage books and physical copies; students can search the catalog and see real-time availability.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** CATL-01, CATL-02, CATL-03, CATL-04, CATL-05, CATL-06, CATS-01, CATS-02
**Success Criteria** (what must be TRUE):

  1. A librarian can add a book by typing details manually or by entering an ISBN and having title, author, and description auto-populated from the Open Library API.
  2. A librarian can edit book details, soft-delete a book (loan history is preserved), add physical copies, and mark a copy as lost.
  3. A student can search the catalog by title, author, or ISBN and see matching results with an accurate count of currently available copies.
  4. Book availability updates immediately after a copy's status changes — no stale counts visible to students.

**Plans:** 3/3 plans complete

**Wave 0** — Dev Infrastructure (blocks all other plans)

- [x] 02-01-PLAN.md — shadcn init + path alias + AppLayout/NavBar shell + Alembic 0003 indexes

**Wave 1** *(blocked on Wave 0 completion)*

- [x] 02-02-PLAN.md — Backend catalog API: books CRUD + copies + ISBN fetch service (CATL-01 through CATL-06, CATS-01, CATS-02)

**Wave 2** *(blocked on Wave 0 and Wave 1 completion)*

- [x] 02-03-PLAN.md — Frontend catalog UI: CatalogPage + LibrarianBooksPage + AddBookPage + BookDetailPage + all helper components (CATL-01 through CATL-06, CATS-01, CATS-02)

**UI hint:** yes

### Phase 3: Loans & Circulation

**Goal:** Librarians can process checkouts and returns; overdue loans are flagged automatically; both roles have dashboard visibility over all active and overdue loans.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** LOAN-01, LOAN-02, LOAN-03, LOAN-04, LOAN-05, LOAN-06
**Success Criteria** (what must be TRUE):

  1. A librarian can check out a specific physical copy to a student, creating an active loan with a due date.
  2. A librarian can process a return for any active loan, updating the copy's status back to available.
  3. Loans whose due date has passed are automatically flagged as overdue without any manual action.
  4. A student can view all their active loans with due dates; a librarian can view all active loans and a filtered list of overdue loans across all students.

**Plans:** 3/3 plans complete

**Wave 1**

- [x] 03-01-PLAN.md — Loan model + Alembic migration 0005 + loans backend API (checkout, return, active/overdue list)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — NavBar extensions + Librarian Loans Dashboard (active/overdue tabs, Return action) + Checkout modal on Book Detail

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-03-PLAN.md — Student My Loans page (card list, overdue badge, empty state) + /my-loans route

**UI hint:** yes

### Phase 4: Fines & Notifications

**Goal:** Overdue fines are calculated and tracked automatically on return; librarians can record payments and waivers; students receive proactive email reminders before and after due dates.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** FINE-01, FINE-02, FINE-03, NOTIF-01, NOTIF-02
**Success Criteria** (what must be TRUE):

  1. When a librarian returns an overdue loan, the system calculates and records the fine (days overdue × daily rate) without manual input.
  2. A librarian can mark a fine as paid or waive it with a reason note; the fine status updates immediately in the ledger.
  3. The system automatically sends a due-date reminder email to a student a configurable number of days before their loan is due.
  4. The system automatically sends an overdue alert email to a student when their loan passes the due date.

**Plans:** 3/3 plans complete

**Wave 1**

- [x] 04-01-PLAN.md — Fine model + Alembic migration 0006 + auto-calculate fine on overdue return (FINE-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Fines pay/waive API + Librarian Fines page (FINE-02, FINE-03)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-03-PLAN.md — Email notification service + APScheduler daily job (NOTIF-01, NOTIF-02)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Auth | 3/3 | Complete    | 2026-06-08 |
| 2. Catalog | 3/3 | Complete    | 2026-06-09 |
| 3. Loans & Circulation | 3/3 | Complete   | 2026-06-09 |
| 4. Fines & Notifications | 3/3 | Complete   | 2026-06-09 |
