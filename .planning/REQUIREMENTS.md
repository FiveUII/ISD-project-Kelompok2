# Requirements — Library Management System

**Version:** v1
**Status:** Scoped
**Last updated:** 2026-06-08

---

## v1 Requirements

### Authentication (AUTH)

- [x] **AUTH-01**: User can log in with email and password and remain logged in across sessions
- [x] **AUTH-02**: Student can self-register with email and password (email verification required before first login)
- [x] **AUTH-03**: User can reset their password via an emailed link
- [x] **AUTH-04**: Role-based access enforced at API level — students cannot access librarian endpoints; librarians have full access

### Catalog — Librarian Management (CAT-L)

- [x] **CATL-01**: Librarian can add a book by entering title, author, ISBN, and description manually
- [x] **CATL-02**: Librarian can auto-fetch book details (title, author, description) by entering an ISBN (Open Library API)
- [x] **CATL-03**: Librarian can edit any book's details
- [x] **CATL-04**: Librarian can soft-delete a book (preserves loan history)
- [x] **CATL-05**: Librarian can add physical copies of a book (each copy tracked individually with a status: available / on loan / lost)
- [x] **CATL-06**: Librarian can update the status of a physical copy (e.g., mark as lost)

### Catalog — Student Search (CAT-S)

- [x] **CATS-01**: Student can search the catalog by title, author, or ISBN
- [x] **CATS-02**: Student can see how many copies of each book are currently available

### Loans — Circulation (LOAN)

- [x] **LOAN-01**: Librarian can check out a specific copy to a student (creates an active loan with a due date)
- [x] **LOAN-02**: Librarian can process a return for an active loan
- [x] **LOAN-03**: System automatically flags loans as overdue when due date passes
- [x] **LOAN-04**: Student can view all their currently active loans with due dates
- [x] **LOAN-05**: Librarian can view all active loans across all students
- [x] **LOAN-06**: Librarian can view all overdue loans

### Fines (FINE)

- [x] **FINE-01**: System automatically calculates a fine when an overdue loan is returned (days overdue × fixed daily rate)
- [ ] **FINE-02**: Librarian can mark a fine as paid (manual cash/offline payment recording)
- [ ] **FINE-03**: Librarian can waive a fine with a reason note

### Notifications (NOTIF)

- [ ] **NOTIF-01**: System sends an email reminder to the student a fixed number of days before their loan is due
- [ ] **NOTIF-02**: System sends an email alert to the student when their loan becomes overdue

---

## v2 Requirements (Deferred)

### Self-Service

- Student can view full loan history (all past loans)
- Student can view outstanding fine balance
- Student can request a renewal on an active loan

### Catalog Enhancements

- Book cover images via Open Library Covers API
- Bulk ISBN import from CSV

### Reservations

- Student can place a hold on an unavailable book
- Student receives email notification when held book becomes available

### Configuration

- Librarian can configure loan period (days), daily fine rate, and reminder window via settings panel

### Reporting

- Librarian can view most-borrowed books report
- Librarian can export loan history (CSV)

---

## Out of Scope

- Mobile app — web-only for v1
- E-books / digital content — physical books only
- Student self-checkout or RFID/barcode scanning — librarian-processed only
- Payment gateway — fine payments recorded manually by librarian
- Multi-branch support — single library only
- External system integrations (MARC21, SIP2, etc.)
- Social features (reviews, ratings, recommendations)
- Reporting/analytics — deferred to v2
- Email provider configuration UI — hardcoded SMTP config in environment variables

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| CATL-01 | Phase 2 | Complete |
| CATL-02 | Phase 2 | Complete |
| CATL-03 | Phase 2 | Complete |
| CATL-04 | Phase 2 | Complete |
| CATL-05 | Phase 2 | Complete |
| CATL-06 | Phase 2 | Complete |
| CATS-01 | Phase 2 | Complete |
| CATS-02 | Phase 2 | Complete |
| LOAN-01 | Phase 3 | Complete |
| LOAN-02 | Phase 3 | Complete |
| LOAN-03 | Phase 3 | Complete |
| LOAN-04 | Phase 3 | Complete |
| LOAN-05 | Phase 3 | Complete |
| LOAN-06 | Phase 3 | Complete |
| FINE-01 | Phase 4 | Complete |
| FINE-02 | Phase 4 | Pending |
| FINE-03 | Phase 4 | Pending |
| NOTIF-01 | Phase 4 | Pending |
| NOTIF-02 | Phase 4 | Pending |

---

## Definition of Done

A v1 requirement is done when:

1. The feature is implemented and accessible in the running Docker Compose stack
2. The API endpoint returns correct data (verified manually or by automated test)
3. The UI reflects the correct state after each action
4. Role-based access is enforced (student cannot call librarian endpoints)
